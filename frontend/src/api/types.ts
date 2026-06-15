/** Matches backend `ProductUnit` choices. */
export const PRODUCT_UNITS = ['kg', 'g', 'L', 'mL', 'unit'] as const;
export type ProductUnit = (typeof PRODUCT_UNITS)[number];

export type AuthSession = {
  /** Snowflake id — always string (JSON number loses precision). */
  userId: string;
  email: string;
  access: string;
  refresh: string;
};

export type Product = {
  product_id: number;
  name: string;
  description: string;
  sku: string;
  unit: string;
  created_at: string;
  updated_at: string;
  quantity_on_hand: string;
  total_qty_purchased: string;
  total_qty_sold: string;
  total_cost: string;
  total_revenue: string;
  profit: string;
  margin_percent: string | null;
};

export type PurchaseOrder = {
  purchase_order_id: number;
  product_id: number;
  quantity: string;
  total_cost: string;
  guid: string;
  created_at: string;
};

export type SalesOrder = {
  sales_order_id: number;
  product_id: number;
  quantity: string;
  unit_price: string;
  guid: string;
  created_at: string;
};

export type StockAddResult = {
  sku: string;
  quantity_on_hand: string;
};
