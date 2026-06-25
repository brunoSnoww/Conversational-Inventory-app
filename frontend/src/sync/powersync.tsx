import type {
  PowerSyncBackendConnector,
  RequiredAdditionalConnectionOptions,
  StreamingSyncImplementation,
} from '@powersync/common';
import { PowerSyncContext } from '@powersync/react';
import {
  PowerSyncDatabase,
  WebRemote,
  WebStreamingSyncImplementation,
  type WebStreamingSyncImplementationOptions,
} from '@powersync/web';
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { createChatCollection, type ChatCollection } from './chat';
import { createPowerSyncFetch, InventoryConnector, type AccessTokenProvider } from './connector';
import { syncLog } from './logger';
import { AppSchema } from './schema';

/** Bump when AppSchema or sync config changes — new db filename forces full resync. */
const SCHEMA_VERSION = 'v7';

/**
 * PowerSync HTTP calls (write-checkpoint) need ngrok-safe routing on Vercel.
 * WebSocket sync still uses the public PowerSync URL from /api/sync/token/.
 */
class InventoryPowerSyncDatabase extends PowerSyncDatabase {
  protected generateSyncStreamImplementation(
    connector: PowerSyncBackendConnector,
    options: RequiredAdditionalConnectionOptions,
  ): StreamingSyncImplementation {
    if (this.resolvedFlags.ssrMode || this.resolvedFlags.enableMultiTabs) {
      return super.generateSyncStreamImplementation(connector, options);
    }

    const remote = new WebRemote(connector, this.logger, {
      fetchImplementation: createPowerSyncFetch(),
    });
    const syncOptions: WebStreamingSyncImplementationOptions = {
      ...(this.options as object),
      ...options,
      flags: this.resolvedFlags,
      adapter: this.bucketStorageAdapter,
      remote,
      uploadCrud: async () => {
        await this.waitForReady();
        await connector.uploadData(this);
      },
      identifier: this.database.name,
      logger: this.logger,
    };
    return new WebStreamingSyncImplementation(syncOptions);
  }
}

function dbFilename(userId: string): string {
  return `inv-${SCHEMA_VERSION}-u${userId}.db`;
}

async function localProductCount(instance: PowerSyncDatabase): Promise<number> {
  const row = await instance.getOptional<{ c: number }>('SELECT COUNT(*) AS c FROM product');
  return Number(row?.c ?? 0);
}

/**
 * PowerSync can report hasSynced while sending 0 ops when ps_buckets still holds a
 * stale checkpoint. Clear + reconnect once before surfacing an empty replica.
 */
async function waitForPopulatedReplica(
  instance: PowerSyncDatabase,
  connector: InventoryConnector,
): Promise<void> {
  await instance.waitForFirstSync();
  if ((await localProductCount(instance)) > 0) {
    return;
  }
  await instance.disconnectAndClear();
  await instance.connect(connector);
  await instance.waitForFirstSync();
}

function attachSyncDebugListeners(instance: PowerSyncDatabase): void {
  instance.registerListener({
    statusChanged: (status) => {
      syncLog.info('powersync status', {
        connected: status.connected,
        connecting: status.connecting,
        hasSynced: status.hasSynced,
        downloading: status.dataFlowStatus.downloading,
        uploading: status.dataFlowStatus.uploading,
        lastSyncedAt: status.lastSyncedAt?.toISOString(),
        downloadError: status.dataFlowStatus.downloadError?.message,
      });
    },
  });
}

export class PowerSyncManager {
  private static instance: PowerSyncManager | null = null;

  private db: PowerSyncDatabase | null = null;
  private initPromise: Promise<PowerSyncDatabase> | null = null;
  private chatCollection: ChatCollection | null = null;

  static getInstance(): PowerSyncManager {
    if (!PowerSyncManager.instance) {
      PowerSyncManager.instance = new PowerSyncManager();
    }
    return PowerSyncManager.instance;
  }

  async initialize(getAccessToken: AccessTokenProvider, userId: string): Promise<PowerSyncDatabase> {
    if (this.db) {
      return this.db;
    }
    if (this.initPromise) {
      return this.initPromise;
    }

    this.initPromise = (async () => {
      this.chatCollection = null;
      const connector = new InventoryConnector(getAccessToken);
      const instance = new InventoryPowerSyncDatabase({
        schema: AppSchema,
        database: { dbFilename: dbFilename(userId) },
        flags: { enableMultiTabs: false, useWebWorker: true },
      });

      try {
        await instance.init();
        await instance.disconnectAndClear();
        await instance.connect(connector);
        attachSyncDebugListeners(instance);
        syncLog.info('init connected', { userId, dbFile: dbFilename(userId) });
        await waitForPopulatedReplica(instance, connector);
        this.chatCollection = createChatCollection(instance);
        this.db = instance;
        return instance;
      } catch (err) {
        syncLog.error('init failed', err);
        await instance.close({ disconnect: false }).catch(() => undefined);
        throw err;
      } finally {
        this.initPromise = null;
      }
    })();

    return this.initPromise;
  }

  /** Logout: wipe local DB. Same filename on next login gets disconnectAndClear before connect. */
  async disconnect(): Promise<void> {
    if (this.initPromise) {
      try {
        await this.initPromise;
      } catch {
        // init failed — still proceed with cleanup
      }
    }

    this.chatCollection = null;
    if (!this.db) {
      return;
    }

    await this.db.disconnectAndClear();
    await this.db.close({ disconnect: false });
    this.db = null;
  }

  getChatCollection(): ChatCollection {
    if (!this.chatCollection) {
      throw new Error('Chat collection not ready — PowerSync not initialized');
    }
    return this.chatCollection;
  }

  tryGetChatCollection(): ChatCollection | null {
    return this.chatCollection;
  }

  getDatabase(): PowerSyncDatabase | null {
    return this.db;
  }
}

type SyncStatus = 'off' | 'connecting' | 'ready' | 'error';

type SyncContextValue = {
  status: SyncStatus;
  error: string | null;
};

const SyncContext = createContext<SyncContextValue>({ status: 'off', error: null });

export function useSyncStatus() {
  return useContext(SyncContext);
}

type ProviderProps = {
  enabled: boolean;
  accessToken: string | null;
  userId: string | null;
  children: ReactNode;
};

export function InventoryPowerSyncProvider({ enabled, accessToken, userId, children }: ProviderProps) {
  const [status, setStatus] = useState<SyncStatus>('off');
  const [error, setError] = useState<string | null>(null);
  const [database, setDatabase] = useState<PowerSyncDatabase | null>(null);

  useEffect(() => {
    let cancelled = false;
    const manager = PowerSyncManager.getInstance();

    async function run() {
      setDatabase(null);
      setError(null);

      if (!enabled || !accessToken || !userId) {
        setStatus('off');
        await manager.disconnect();
        return;
      }

      setStatus('connecting');
      syncLog.info('provider connecting', { userId });
      try {
        const db = await manager.initialize(() => accessToken, userId);
        if (cancelled) {
          syncLog.warn('provider cancelled after init', { userId });
          return;
        }
        setDatabase(db);
        setStatus('ready');
        syncLog.info('provider ready', { userId, hasContext: true });
      } catch (err) {
        if (!cancelled) {
          syncLog.error('provider error', err);
          setStatus('error');
          setError('Could not connect. Please try again.');
          setDatabase(null);
        }
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [enabled, accessToken, userId]);

  const syncCtx = useMemo(() => ({ status, error }), [status, error]);

  const body = database ? (
    <PowerSyncContext.Provider value={database}>{children}</PowerSyncContext.Provider>
  ) : (
    children
  );

  return <SyncContext.Provider value={syncCtx}>{body}</SyncContext.Provider>;
}
