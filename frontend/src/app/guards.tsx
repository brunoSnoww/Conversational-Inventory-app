import type { ReactNode } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';
import { routes } from '../routes';
import { InventoryPowerSyncProvider } from '../sync/powersync';

const POWERSYNC_ENABLED = import.meta.env.VITE_ENABLE_POWERSYNC !== 'false';

export function AuthenticatedLayout() {
  const { session } = useAuth();
  const location = useLocation();

  if (!session) {
    return <Navigate to={routes.login} state={{ from: location }} replace />;
  }

  return (
    <InventoryPowerSyncProvider
      enabled={POWERSYNC_ENABLED}
      accessToken={session.access}
      userId={session.userId}
    >
      <Outlet />
    </InventoryPowerSyncProvider>
  );
}

export function GuestRoute({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  const location = useLocation();

  if (session) {
    const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
    return <Navigate to={from ?? routes.dashboard} replace />;
  }

  return <>{children}</>;
}
