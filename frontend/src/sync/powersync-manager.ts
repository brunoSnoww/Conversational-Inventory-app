import type { PowerSyncDatabase } from '@powersync/web';

import { createChatCollection, type ChatCollection } from './chat';
import { InventoryConnector, type AccessTokenProvider } from './connector';
import { InventoryPowerSyncDatabase } from './inventory-powersync-database';
import { syncLog } from './logger';
import { AppSchema } from './schema';

/** Bump when AppSchema or sync config changes — new db filename forces full resync. */
const SCHEMA_VERSION = 'v6';

function dbFilename(userId: string): string {
  return `inv-${SCHEMA_VERSION}-u${userId}.db`;
}

async function localChatCount(instance: PowerSyncDatabase): Promise<number> {
  const row = await instance.getOptional<{ c: number }>('SELECT COUNT(*) AS c FROM chat_message');
  return Number(row?.c ?? 0);
}

async function logChatSnapshot(instance: PowerSyncDatabase, label: string): Promise<void> {
  const rows = await instance.getAll<{ chat_message_id: string; role: string; content: string }>(
    `SELECT chat_message_id, role, substr(content, 1, 50) AS content
     FROM chat_message ORDER BY created_at DESC LIMIT 4`,
  );
  syncLog.info(`chat sqlite [${label}]`, {
    count: await localChatCount(instance),
    tail: rows.map((r) => ({ id: r.chat_message_id, role: r.role, content: r.content })),
  });
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
      if (!status.dataFlowStatus.downloading && status.connected) {
        void logChatSnapshot(instance, 'after-download');
      }
    },
  });
}

async function localProductCount(instance: PowerSyncDatabase): Promise<number> {
  const row = await instance.getOptional<{ c: number }>('SELECT COUNT(*) AS c FROM product');
  return Number(row?.c ?? 0);
}

/**
 * PowerSync can report hasSynced while sending 0 ops when ps_buckets still holds a
 * stale checkpoint (disconnectAndClear clears data tables but clients reconnect at the
 * server checkpoint). Clear + reconnect once before surfacing an empty replica.
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
        await logChatSnapshot(instance, 'init-done');
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
