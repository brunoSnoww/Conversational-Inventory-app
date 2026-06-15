/**
 * Reactive read hooks — display truth from PowerSync local SQLite.
 *
 * Two read styles coexist (both reactive, both from the synced replica):
 * - `useDashboard`: raw SQLite query via @powersync/react. Right tool for a
 *   multi-table aggregate (stock + PO + SO) over decimal-as-text columns —
 *   SQLite does the coercion + grouping that a TanStack DB query builder can't.
 * - `useChatMessages`: TanStack DB live query over the `chat_message`
 *   collection. Pairs with optimistic inserts (see `chat.ts`).
 */
import { useQuery as usePowerSyncQuery } from '@powersync/react';
import { useLiveQuery } from '@tanstack/react-db';

import { tryGetChatCollection } from './collections';
import {
  PRODUCTS_DASHBOARD,
  PRODUCT_BY_SKU,
  PURCHASE_ORDERS,
  SALES_ORDERS,
  STOCK_MOVEMENTS,
} from './queries';

export type DashboardRow = {
  product_id: string;
  sku: string;
  name: string;
  unit: string;
  quantity_on_hand: number;
  total_qty_purchased: number;
  total_cost: number;
  total_qty_sold: number;
  total_revenue: number;
  profit: number;
  margin_percent: number | null;
};

export function useDashboard() {
  return usePowerSyncQuery<DashboardRow>(PRODUCTS_DASHBOARD);
}

export type PurchaseOrderRow = {
  purchase_order_id: string;
  user_id: string;
  product_id: string;
  quantity: string;
  total_cost: string;
  guid: string;
  created_at: string;
  sku: string;
  product_name: string;
};

export type SalesOrderRow = {
  sales_order_id: string;
  user_id: string;
  product_id: string;
  quantity: string;
  unit_price: string;
  guid: string;
  created_at: string;
  sku: string;
  product_name: string;
};

export type StockMovementRow = {
  stock_movement_id: string;
  user_id: string;
  product_id: string;
  quantity_delta: string;
  unit_cost: string | null;
  source: string;
  source_id: string | null;
  created_at: string;
  sku: string;
};

export type ProductRow = {
  product_id: string;
  user_id: string;
  name: string;
  description: string;
  sku: string;
  unit: string;
  created_at: string;
  updated_at: string;
};

export function useProductBySku(sku: string | undefined) {
  return usePowerSyncQuery<ProductRow>(PRODUCT_BY_SKU, sku ? [sku] : ['']);
}

export function usePurchaseOrders() {
  return usePowerSyncQuery<PurchaseOrderRow>(PURCHASE_ORDERS);
}

export function useSalesOrders() {
  return usePowerSyncQuery<SalesOrderRow>(SALES_ORDERS);
}

export function useStockMovements() {
  return usePowerSyncQuery<StockMovementRow>(STOCK_MOVEMENTS);
}

export function useChatMessages() {
  const collection = tryGetChatCollection();
  return useLiveQuery(
    (q) =>
      collection
        ? q.from({ m: collection }).orderBy(({ m }) => m.created_at, 'asc')
        : null,
    [collection],
  );
}
