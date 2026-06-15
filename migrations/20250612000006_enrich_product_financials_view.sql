-- +goose Up
-- Per-SKU dashboard aggregate: stock + bought/sold quantities + financials in one read model.

DROP VIEW IF EXISTS product_financials_view;

CREATE VIEW product_financials_view AS
SELECT
    p.user_id,
    p.product_id,
    p.sku,
    p.name,
    p.unit,
    COALESCE(st.quantity_on_hand, 0)::NUMERIC(20, 4) AS quantity_on_hand,
    COALESCE(po_agg.total_qty_purchased, 0)::NUMERIC(20, 4) AS total_qty_purchased,
    COALESCE(po_agg.total_purchase_cost, 0)::NUMERIC(20, 2) AS total_cost,
    COALESCE(so_agg.total_qty_sold, 0)::NUMERIC(20, 4) AS total_qty_sold,
    COALESCE(so_agg.total_revenue, 0)::NUMERIC(20, 2) AS total_revenue,
    (COALESCE(so_agg.total_revenue, 0) - COALESCE(po_agg.total_purchase_cost, 0))::NUMERIC(20, 2) AS profit
FROM product p
LEFT JOIN product_stock_view st USING (user_id, product_id)
LEFT JOIN (
    SELECT user_id, product_id, SUM(quantity) AS total_qty_purchased, SUM(total_cost) AS total_purchase_cost
    FROM purchase_order
    GROUP BY user_id, product_id
) po_agg USING (user_id, product_id)
LEFT JOIN (
    SELECT user_id, product_id, SUM(quantity) AS total_qty_sold, SUM(quantity * unit_price) AS total_revenue
    FROM sales_order
    GROUP BY user_id, product_id
) so_agg USING (user_id, product_id);

-- +goose Down
DROP VIEW IF EXISTS product_financials_view;

CREATE VIEW product_financials_view AS
SELECT
    p.user_id,
    p.product_id,
    p.sku,
    p.name,
    p.unit,
    COALESCE(po_agg.total_purchase_cost, 0)::NUMERIC(20, 2) AS total_cost,
    COALESCE(so_agg.total_revenue, 0)::NUMERIC(20, 2) AS total_revenue,
    (COALESCE(so_agg.total_revenue, 0) - COALESCE(po_agg.total_purchase_cost, 0))::NUMERIC(20, 2) AS profit
FROM product p
LEFT JOIN (
    SELECT user_id, product_id, SUM(total_cost) AS total_purchase_cost
    FROM purchase_order
    GROUP BY user_id, product_id
) po_agg USING (user_id, product_id)
LEFT JOIN (
    SELECT user_id, product_id, SUM(quantity * unit_price) AS total_revenue
    FROM sales_order
    GROUP BY user_id, product_id
) so_agg USING (user_id, product_id);
