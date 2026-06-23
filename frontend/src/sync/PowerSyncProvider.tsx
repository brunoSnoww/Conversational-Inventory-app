import { PowerSyncContext } from '@powersync/react';
import type { PowerSyncDatabase } from '@powersync/web';
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { syncLog } from './logger';
import { PowerSyncManager } from './powersync-manager';

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
