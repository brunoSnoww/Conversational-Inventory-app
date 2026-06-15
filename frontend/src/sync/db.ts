import { PowerSyncDatabase } from '@powersync/web';

import { createChatCollection, setChatCollection } from './collections';
import { InventoryConnector, type AccessTokenProvider } from './connector';
import { syncLog } from './logger';
import { AppSchema } from './schema';

/** Bump when AppSchema changes — new db filename forces full resync. */
const SCHEMA_VERSION = 'v5';

let db: PowerSyncDatabase | null = null;
/** Serializes init across React Strict Mode double-mount. */
let initPromise: Promise<PowerSyncDatabase> | null = null;

function dbFilename(userId: string): string {
  return `inv-${SCHEMA_VERSION}-u${userId}.db`;
}

export function getPowerSyncDb(): PowerSyncDatabase {
  if (!db) {
    throw new Error('PowerSync not initialized — call initPowerSync() after login');
  }
  return db;
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

export async function initPowerSync(
  getAccessToken: AccessTokenProvider,
  userId: string,
): Promise<PowerSyncDatabase> {
  if (db) {
    return db;
  }
  if (initPromise) {
    return initPromise;
  }

  const apiBaseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

  initPromise = (async () => {
    setChatCollection(null);
    const connector = new InventoryConnector(apiBaseUrl, getAccessToken);
    const instance = new PowerSyncDatabase({
      schema: AppSchema,
      database: { dbFilename: dbFilename(userId) },
      flags: { enableMultiTabs: false, useWebWorker: true },
    });

    try {
      await instance.init();
      // Wipe stale bucket checkpoints from prior sessions in this IndexedDB file.
      await instance.disconnectAndClear();
      await instance.connect(connector);
      await waitForPopulatedReplica(instance, connector);
      setChatCollection(createChatCollection(instance));
      db = instance;
      return instance;
    } catch (err) {
      syncLog.error('init failed', err);
      await instance.close({ disconnect: false }).catch(() => undefined);
      throw err;
    } finally {
      initPromise = null;
    }
  })();

  return initPromise;
}

/** Logout: wipe local DB. Same filename on next login gets disconnectAndClear before connect. */
export async function disconnectPowerSync(clear = false): Promise<void> {
  if (initPromise) {
    try {
      await initPromise;
    } catch {
      // init failed — still proceed with cleanup
    }
  }

  setChatCollection(null);
  if (!db) {
    return;
  }

  if (clear) {
    await db.disconnectAndClear();
  } else {
    await db.disconnect();
  }
  await db.close({ disconnect: false });
  db = null;
}
