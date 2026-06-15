/**
 * SQLite read queries — display truth from PowerSync, never REST-fetch these tables.
 *
 * Base tables replicate down (product, purchase_order,
 * sales_order, stock_movement, chat_message), and read models are computed
 * client-side. PowerSync sync rules cannot GROUP BY / JOIN, and Postgres views
 * are not published — so the `product_financials_view` aggregate is mirrored
 * here as a reactive SQLite query over the synced base tables.
 */

/**
 * Per-SKU dashboard row. Mirrors server `product_financials_view`
 * (migration 000006): stock on hand + bought/sold qty + cost/revenue/profit.
 * `margin_percent` is derived (matches `format_margin_percent` on the API).
 */
export const PRODUCTS_DASHBOARD = `
  SELECT
    p.product_id,
    p.sku,
    p.name,
    p.unit,
    COALESCE(sm.quantity_on_hand, 0) AS quantity_on_hand,
    COALESCE(po.total_qty_purchased, 0) AS total_qty_purchased,
    COALESCE(po.total_cost, 0) AS total_cost,
    COALESCE(so.total_qty_sold, 0) AS total_qty_sold,
    COALESCE(so.total_revenue, 0) AS total_revenue,
    (COALESCE(so.total_revenue, 0) - COALESCE(po.total_cost, 0)) AS profit,
    CASE
      WHEN COALESCE(po.total_cost, 0) > 0
      THEN ROUND((COALESCE(so.total_revenue, 0) - COALESCE(po.total_cost, 0)) / po.total_cost * 100, 2)
      ELSE NULL
    END AS margin_percent
  FROM product p
  LEFT JOIN (
    SELECT product_id, SUM(quantity_delta) AS quantity_on_hand
    FROM stock_movement
    GROUP BY product_id
  ) sm ON sm.product_id = p.product_id
  LEFT JOIN (
    SELECT product_id,
      SUM(quantity) AS total_qty_purchased,
      SUM(total_cost) AS total_cost
    FROM purchase_order
    GROUP BY product_id
  ) po ON po.product_id = p.product_id
  LEFT JOIN (
    SELECT product_id,
      SUM(quantity) AS total_qty_sold,
      SUM(quantity * unit_price) AS total_revenue
    FROM sales_order
    GROUP BY product_id
  ) so ON so.product_id = p.product_id
  ORDER BY p.sku ASC
`;

export const PRODUCT_BY_SKU = `
  SELECT *
  FROM product
  WHERE lower(sku) = lower(?)
  LIMIT 1
`;

export const PURCHASE_ORDERS = `
  SELECT po.*, p.sku, p.name AS product_name
  FROM purchase_order po
  JOIN product p ON p.product_id = po.product_id
  ORDER BY po.created_at DESC
`;

export const SALES_ORDERS = `
  SELECT so.*, p.sku, p.name AS product_name
  FROM sales_order so
  JOIN product p ON p.product_id = so.product_id
  ORDER BY so.created_at DESC
`;

export const STOCK_MOVEMENTS = `
  SELECT sm.*, p.sku
  FROM stock_movement sm
  JOIN product p ON p.product_id = sm.product_id
  ORDER BY sm.created_at DESC
`;
