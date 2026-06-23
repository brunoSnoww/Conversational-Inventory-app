/**
 * Reactive read hooks — display truth from PowerSync local SQLite.
 *
 * `useDashboard` uses raw SQLite via @powersync/react for multi-table aggregates
 * (stock + PO + SO) over decimal-as-text columns. Chat reads live in `chat.ts`.
 */
import { useQuery as usePowerSyncQuery } from '@powersync/react';

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
  const key = sku?.trim() || '__no_sku__';
  return usePowerSyncQuery<ProductRow>(PRODUCT_BY_SKU, [key]);
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
