/**
 * Single reactive subscription for product_financials_summary shared by Dashboard + Products.
 */
import { createContext, useContext, type ReactNode } from 'react';
import { Outlet } from 'react-router-dom';

import { useDashboard } from './hooks';

export type DashboardRead = ReturnType<typeof useDashboard>;

const DashboardReadContext = createContext<DashboardRead | null>(null);

/** Layout route: call once per shell session while on dashboard or catalog routes. */
export function DashboardReadProvider({ children }: { children?: ReactNode }) {
  const dashboard = useDashboard();

  return (
    <DashboardReadContext.Provider value={dashboard}>
      {children ?? <Outlet />}
    </DashboardReadContext.Provider>
  );
}

export function useDashboardRead(): DashboardRead {
  const ctx = useContext(DashboardReadContext);
  if (!ctx) {
    throw new Error('useDashboardRead must be used within DashboardReadProvider');
  }
  return ctx;
}
