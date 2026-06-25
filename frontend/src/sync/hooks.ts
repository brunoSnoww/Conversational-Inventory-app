/**
 * Reactive read hooks — display truth from PowerSync local SQLite.
 *
 * Complex aggregates and JOINs live on Postgres (triggers + denormalized columns);
 * the client runs flat SELECTs only.
 */
import { useQuery as usePowerSyncQuery } from '@powersync/react';

const PRODUCTS_DASHBOARD = `
  SELECT
    product_id,
    sku,
    name,
    unit,
    quantity_on_hand,
    total_qty_purchased,
    total_cost,
    total_qty_sold,
    total_revenue,
    profit,
    margin_percent
  FROM product_financials_summary
  ORDER BY sku ASC
`;

const PRODUCT_BY_SKU = `
  SELECT *
  FROM product
  WHERE lower(sku) = lower(?)
  LIMIT 1
`;

const PURCHASE_ORDERS = `
  SELECT *
  FROM purchase_order
  ORDER BY created_at DESC
`;

const SALES_ORDERS = `
  SELECT *
  FROM sales_order
  ORDER BY created_at DESC
`;

const STOCK_MOVEMENTS = `
  SELECT *
  FROM stock_movement
  ORDER BY created_at DESC
`;

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
  product_sku: string;
  product_name: string;
  guid: string;
  created_at: string;
};

export type SalesOrderRow = {
  sales_order_id: string;
  user_id: string;
  product_id: string;
  quantity: string;
  unit_price: string;
  product_sku: string;
  product_name: string;
  guid: string;
  created_at: string;
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
  product_sku: string;
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
