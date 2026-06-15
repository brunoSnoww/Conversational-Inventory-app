import { PowerSyncContext } from '@powersync/react';
import type { PowerSyncDatabase } from '@powersync/web';
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { disconnectPowerSync, initPowerSync } from './db';
import { syncLog } from './logger';

type SyncStatus = 'off' | 'connecting' | 'ready' | 'error';

type SyncContextValue = {
  status: SyncStatus;
  error: string | null;
};

const SyncContext = createContext<SyncContextValue>({ status: 'off', error: null });

export function useSyncStatus() {
  return useContext(SyncContext);
}

type Props = {
  enabled: boolean;
  accessToken: string | null;
  userId: string | null;
  children: ReactNode;
};

export function InventoryPowerSyncProvider({ enabled, accessToken, userId, children }: Props) {
  const [status, setStatus] = useState<SyncStatus>('off');
  const [error, setError] = useState<string | null>(null);
  const [database, setDatabase] = useState<PowerSyncDatabase | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setDatabase(null);
      setError(null);

      if (!enabled || !accessToken || !userId) {
        setStatus('off');
        await disconnectPowerSync(true);
        return;
      }

      setStatus('connecting');
      try {
        const db = await initPowerSync(() => accessToken, userId);
        if (cancelled) {
          return;
        }
        setDatabase(db);
        await db.waitForFirstSync();
        if (cancelled) {
          return;
        }
        setStatus('ready');
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
