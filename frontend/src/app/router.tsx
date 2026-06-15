import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { AuthenticatedLayout, GuestRoute } from './guards';
import { AppShellLayout } from './shell';
import { LoginPage } from '../features/login';
import {
  ActivityPage,
  DashboardPage,
  ProductDetailPage,
  ProductsPage,
  PurchasesPage,
  SalesPage,
  StockPage,
} from '../features/inventory';
import { Muted, Page } from '../features/ui';
import { routes } from '../routes';

const LazyChatPage = lazy(() =>
  import('../features/chat').then((m) => ({ default: m.ChatPage })),
);

function ChatRoute() {
  return (
    <Suspense fallback={<Page title="Chat"><Muted>Loading…</Muted></Page>}>
      <LazyChatPage />
    </Suspense>
  );
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path={routes.login} element={<GuestRoute><LoginPage /></GuestRoute>} />
        <Route element={<AuthenticatedLayout />}>
          <Route element={<AppShellLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="products" element={<ProductsPage />} />
            <Route path="products/:sku" element={<ProductDetailPage />} />
            <Route path="stock" element={<StockPage />} />
            <Route path="purchases" element={<PurchasesPage />} />
            <Route path="sales" element={<SalesPage />} />
            <Route path="activity" element={<ActivityPage />} />
            <Route path="chat" element={<ChatRoute />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to={routes.dashboard} replace />} />
      </Routes>
    </BrowserRouter>
  );
}
