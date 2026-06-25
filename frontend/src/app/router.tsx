import { lazy, Suspense } from 'react';
import { Stack } from '@mantine/core';
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
import { Muted } from '../features/ui';
import { routes } from '../routes';
import { DashboardReadProvider } from '../sync';

const LazyChatPage = lazy(() =>
  import('../features/chat').then((m) => ({ default: m.ChatPage })),
);

function ChatRoute() {
  return (
    <Suspense
      fallback={
        <Stack flex={1} mih={0} justify="center" align="center">
          <Muted>Loading…</Muted>
        </Stack>
      }
    >
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
            <Route element={<DashboardReadProvider />}>
              <Route index element={<DashboardPage />} />
              <Route path="products" element={<ProductsPage />} />
            </Route>
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
