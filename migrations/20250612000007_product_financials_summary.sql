-- +goose Up
-- +goose StatementBegin
-- Octopus-style read model: trigger-maintained per-SKU financials synced to PowerSync clients.
-- Replaces client-side JOIN/GROUP BY over stock_movement + purchase_order + sales_order.

CREATE TABLE product_financials_summary (
    product_id BIGINT PRIMARY KEY
        CHECK (product_id > 0)
        REFERENCES product (product_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL
        CHECK (user_id > 0)
        REFERENCES app_user (user_id),
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    unit product_unit NOT NULL,
    quantity_on_hand NUMERIC(20, 4) NOT NULL DEFAULT 0,
    total_qty_purchased NUMERIC(20, 4) NOT NULL DEFAULT 0,
    total_cost NUMERIC(20, 2) NOT NULL DEFAULT 0,
    total_qty_sold NUMERIC(20, 4) NOT NULL DEFAULT 0,
    total_revenue NUMERIC(20, 2) NOT NULL DEFAULT 0,
    profit NUMERIC(20, 2) NOT NULL DEFAULT 0,
    margin_percent NUMERIC(20, 2),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX product_financials_summary_user_sku_idx
    ON product_financials_summary (user_id, lower(sku));

CREATE FUNCTION refresh_product_financials_summary(p_product_id BIGINT) RETURNS void AS $$
DECLARE
    v_user_id BIGINT;
    v_sku TEXT;
    v_name TEXT;
    v_unit product_unit;
    v_qty_on_hand NUMERIC(20, 4);
    v_qty_purchased NUMERIC(20, 4);
    v_total_cost NUMERIC(20, 2);
    v_qty_sold NUMERIC(20, 4);
    v_total_revenue NUMERIC(20, 2);
    v_profit NUMERIC(20, 2);
    v_margin NUMERIC(20, 2);
BEGIN
    SELECT user_id, sku, name, unit
    INTO v_user_id, v_sku, v_name, v_unit
    FROM product
    WHERE product_id = p_product_id;

    IF NOT FOUND THEN
        DELETE FROM product_financials_summary WHERE product_id = p_product_id;
        RETURN;
    END IF;

    SELECT COALESCE(SUM(quantity_delta), 0)
    INTO v_qty_on_hand
    FROM stock_movement
    WHERE product_id = p_product_id;

    SELECT COALESCE(SUM(quantity), 0), COALESCE(SUM(total_cost), 0)
    INTO v_qty_purchased, v_total_cost
    FROM purchase_order
    WHERE product_id = p_product_id;

    SELECT COALESCE(SUM(quantity), 0), COALESCE(SUM(quantity * unit_price), 0)
    INTO v_qty_sold, v_total_revenue
    FROM sales_order
    WHERE product_id = p_product_id;

    v_profit := v_total_revenue - v_total_cost;
    IF v_total_cost > 0 THEN
        v_margin := ROUND((v_profit / v_total_cost) * 100, 2);
    ELSE
        v_margin := NULL;
    END IF;

    INSERT INTO product_financials_summary (
        product_id, user_id, sku, name, unit,
        quantity_on_hand, total_qty_purchased, total_cost,
        total_qty_sold, total_revenue, profit, margin_percent, updated_at
    )
    VALUES (
        p_product_id, v_user_id, v_sku, v_name, v_unit,
        v_qty_on_hand, v_qty_purchased, v_total_cost,
        v_qty_sold, v_total_revenue, v_profit, v_margin, now()
    )
    ON CONFLICT (product_id) DO UPDATE SET
        user_id = EXCLUDED.user_id,
        sku = EXCLUDED.sku,
        name = EXCLUDED.name,
        unit = EXCLUDED.unit,
        quantity_on_hand = EXCLUDED.quantity_on_hand,
        total_qty_purchased = EXCLUDED.total_qty_purchased,
        total_cost = EXCLUDED.total_cost,
        total_qty_sold = EXCLUDED.total_qty_sold,
        total_revenue = EXCLUDED.total_revenue,
        profit = EXCLUDED.profit,
        margin_percent = EXCLUDED.margin_percent,
        updated_at = now();
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION trigger_refresh_product_financials_summary() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        PERFORM refresh_product_financials_summary(OLD.product_id);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.product_id IS DISTINCT FROM NEW.product_id THEN
            PERFORM refresh_product_financials_summary(OLD.product_id);
        END IF;
        PERFORM refresh_product_financials_summary(NEW.product_id);
        RETURN NEW;
    END IF;

    PERFORM refresh_product_financials_summary(NEW.product_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER product_financials_summary_product_trigger
    AFTER INSERT OR UPDATE OR DELETE ON product
    FOR EACH ROW EXECUTE PROCEDURE trigger_refresh_product_financials_summary();

CREATE TRIGGER product_financials_summary_purchase_order_trigger
    AFTER INSERT OR UPDATE OR DELETE ON purchase_order
    FOR EACH ROW EXECUTE PROCEDURE trigger_refresh_product_financials_summary();

CREATE TRIGGER product_financials_summary_sales_order_trigger
    AFTER INSERT OR UPDATE OR DELETE ON sales_order
    FOR EACH ROW EXECUTE PROCEDURE trigger_refresh_product_financials_summary();

CREATE TRIGGER product_financials_summary_stock_movement_trigger
    AFTER INSERT OR UPDATE OR DELETE ON stock_movement
    FOR EACH ROW EXECUTE PROCEDURE trigger_refresh_product_financials_summary();

-- Backfill all existing products (seed + demo data run before this migration).
SELECT refresh_product_financials_summary(product_id) FROM product;

-- Server REST/AI read model now reads the maintained table (no runtime aggregation).
DROP VIEW IF EXISTS product_financials_view;

CREATE VIEW product_financials_view AS
SELECT
    user_id,
    product_id,
    sku,
    name,
    unit::text AS unit,
    quantity_on_hand,
    total_qty_purchased,
    total_cost,
    total_qty_sold,
    total_revenue,
    profit
FROM product_financials_summary;

ALTER PUBLICATION powersync ADD TABLE product_financials_summary;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
ALTER PUBLICATION powersync DROP TABLE product_financials_summary;

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

DROP TRIGGER IF EXISTS product_financials_summary_stock_movement_trigger ON stock_movement;
DROP TRIGGER IF EXISTS product_financials_summary_sales_order_trigger ON sales_order;
DROP TRIGGER IF EXISTS product_financials_summary_purchase_order_trigger ON purchase_order;
DROP TRIGGER IF EXISTS product_financials_summary_product_trigger ON product;

DROP FUNCTION IF EXISTS trigger_refresh_product_financials_summary();
DROP FUNCTION IF EXISTS refresh_product_financials_summary(BIGINT);

DROP TABLE IF EXISTS product_financials_summary;
-- +goose StatementEnd
