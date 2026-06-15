-- +goose Up
-- +goose StatementBegin
-- Inventory core schema: products, orders, event-sourced stock ledger, chat.
-- Patterns: timestamp IDs, per-user scoping, partial indexes, idempotent guid upserts.

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------

CREATE TYPE product_unit AS ENUM ('kg', 'g', 'L', 'mL', 'unit');

CREATE TYPE stock_movement_source AS ENUM ('PURCHASE_ORDER', 'SALES_ORDER', 'MANUAL');

CREATE TYPE chat_message_role AS ENUM ('user', 'assistant');

-- ---------------------------------------------------------------------------
-- Sequences (one per table)
-- ---------------------------------------------------------------------------

CREATE SEQUENCE product_id_seq MINVALUE 0 MAXVALUE 2048 CYCLE;
CREATE SEQUENCE purchase_order_id_seq MINVALUE 0 MAXVALUE 2048 CYCLE;
CREATE SEQUENCE sales_order_id_seq MINVALUE 0 MAXVALUE 2048 CYCLE;
CREATE SEQUENCE stock_movement_id_seq MINVALUE 0 MAXVALUE 2048 CYCLE;
CREATE SEQUENCE chat_message_id_seq MINVALUE 0 MAXVALUE 2048 CYCLE;

-- ---------------------------------------------------------------------------
-- Products (upsert by user_id + lower(sku) — Pattern C variant)
-- ---------------------------------------------------------------------------

CREATE TABLE product (
    product_id BIGINT PRIMARY KEY
        CHECK (product_id > 0)
        DEFAULT gen_random_with_timestamp_id('product_id_seq'),
    user_id BIGINT NOT NULL
        CHECK (user_id > 0)
        REFERENCES app_user (user_id),
    name TEXT NOT NULL
        CHECK (char_length(trim(name)) BETWEEN 1 AND 200),
    description TEXT NOT NULL DEFAULT ''
        CHECK (char_length(description) <= 2000),
    sku TEXT NOT NULL
        CHECK (char_length(trim(sku)) BETWEEN 1 AND 64),
    unit product_unit NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX product_user_sku_unique ON product (user_id, lower(sku));

CREATE INDEX product_user_id_idx ON product (user_id, product_id DESC);

CREATE TRIGGER product_updated_at_trigger
    BEFORE UPDATE ON product
    FOR EACH ROW EXECUTE PROCEDURE updated_at_trigger_function();

-- ---------------------------------------------------------------------------
-- Purchase orders (idempotent via guid — Pattern B: DO NOTHING on conflict)
-- ---------------------------------------------------------------------------

CREATE TABLE purchase_order (
    purchase_order_id BIGINT PRIMARY KEY
        CHECK (purchase_order_id > 0)
        DEFAULT gen_random_with_timestamp_id('purchase_order_id_seq'),
    user_id BIGINT NOT NULL
        CHECK (user_id > 0)
        REFERENCES app_user (user_id),
    product_id BIGINT NOT NULL
        CHECK (product_id > 0)
        REFERENCES product (product_id),
    quantity NUMERIC(20, 4) NOT NULL
        CHECK (quantity > 0),
    total_cost NUMERIC(20, 2) NOT NULL
        CHECK (total_cost >= 0),
    guid UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT purchase_order_user_guid_unique UNIQUE (user_id, guid)
);

CREATE INDEX purchase_order_user_product_idx
    ON purchase_order (user_id, product_id, purchase_order_id DESC);

-- Ensure product belongs to same user as the order.
CREATE FUNCTION enforce_purchase_order_product_owner() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM product p
        WHERE p.product_id = NEW.product_id AND p.user_id = NEW.user_id
    ) THEN
        RAISE EXCEPTION 'product_id % does not belong to user_id %', NEW.product_id, NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER purchase_order_product_owner_trigger
    BEFORE INSERT OR UPDATE ON purchase_order
    FOR EACH ROW EXECUTE PROCEDURE enforce_purchase_order_product_owner();

-- ---------------------------------------------------------------------------
-- Sales orders (idempotent via guid)
-- ---------------------------------------------------------------------------

CREATE TABLE sales_order (
    sales_order_id BIGINT PRIMARY KEY
        CHECK (sales_order_id > 0)
        DEFAULT gen_random_with_timestamp_id('sales_order_id_seq'),
    user_id BIGINT NOT NULL
        CHECK (user_id > 0)
        REFERENCES app_user (user_id),
    product_id BIGINT NOT NULL
        CHECK (product_id > 0)
        REFERENCES product (product_id),
    quantity NUMERIC(20, 4) NOT NULL
        CHECK (quantity > 0),
    unit_price NUMERIC(20, 2) NOT NULL
        CHECK (unit_price >= 0),
    guid UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT sales_order_user_guid_unique UNIQUE (user_id, guid)
);

CREATE INDEX sales_order_user_product_idx
    ON sales_order (user_id, product_id, sales_order_id DESC);

CREATE FUNCTION enforce_sales_order_product_owner() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM product p
        WHERE p.product_id = NEW.product_id AND p.user_id = NEW.user_id
    ) THEN
        RAISE EXCEPTION 'product_id % does not belong to user_id %', NEW.product_id, NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sales_order_product_owner_trigger
    BEFORE INSERT OR UPDATE ON sales_order
    FOR EACH ROW EXECUTE PROCEDURE enforce_sales_order_product_owner();

-- ---------------------------------------------------------------------------
-- Stock ledger (append-only event sourcing)
-- Current stock = SUM(quantity_delta) per (user_id, product_id)
-- ---------------------------------------------------------------------------

CREATE TABLE stock_movement (
    stock_movement_id BIGINT PRIMARY KEY
        CHECK (stock_movement_id > 0)
        DEFAULT gen_random_with_timestamp_id('stock_movement_id_seq'),
    user_id BIGINT NOT NULL
        CHECK (user_id > 0)
        REFERENCES app_user (user_id),
    product_id BIGINT NOT NULL
        CHECK (product_id > 0)
        REFERENCES product (product_id),
    quantity_delta NUMERIC(20, 4) NOT NULL
        CHECK (quantity_delta <> 0),
    unit_cost NUMERIC(20, 2)
        CHECK (unit_cost IS NULL OR unit_cost >= 0),
    source stock_movement_source NOT NULL,
    source_id BIGINT
        CHECK (source_id IS NULL OR source_id > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT stock_movement_source_id_present
        CHECK (
            (source = 'MANUAL' AND source_id IS NULL)
            OR (source IN ('PURCHASE_ORDER', 'SALES_ORDER') AND source_id IS NOT NULL)
        )
);

-- Cursor pagination + time-range scans via timestamp-embedded PK.
CREATE INDEX stock_movement_user_product_id_idx
    ON stock_movement (user_id, product_id, stock_movement_id DESC);

-- Partial index: only inbound movements (for cost-basis / FIFO later).
CREATE INDEX stock_movement_open_in_idx
    ON stock_movement (user_id, product_id, stock_movement_id DESC)
    WHERE quantity_delta > 0;

CREATE FUNCTION enforce_stock_movement_product_owner() RETURNS trigger AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM product p
        WHERE p.product_id = NEW.product_id AND p.user_id = NEW.user_id
    ) THEN
        RAISE EXCEPTION 'product_id % does not belong to user_id %', NEW.product_id, NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER stock_movement_product_owner_trigger
    BEFORE INSERT OR UPDATE ON stock_movement
    FOR EACH ROW EXECUTE PROCEDURE enforce_stock_movement_product_owner();

-- ---------------------------------------------------------------------------
-- Chat messages (PowerSync Tier B later; cursor pagination now)
-- ---------------------------------------------------------------------------

CREATE TABLE chat_message (
    chat_message_id BIGINT PRIMARY KEY
        CHECK (chat_message_id > 0)
        DEFAULT gen_random_with_timestamp_id('chat_message_id_seq'),
    user_id BIGINT NOT NULL
        CHECK (user_id > 0)
        REFERENCES app_user (user_id),
    role chat_message_role NOT NULL,
    content TEXT NOT NULL
        CHECK (char_length(content) BETWEEN 1 AND 16000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX chat_message_user_id_idx
    ON chat_message (user_id, chat_message_id DESC);

-- ---------------------------------------------------------------------------
-- Read models (views — profit/stock without app-layer duplication)
-- ---------------------------------------------------------------------------

CREATE VIEW product_stock_view AS
SELECT
    sm.user_id,
    sm.product_id,
    p.sku,
    p.name,
    p.unit,
    SUM(sm.quantity_delta) AS quantity_on_hand
FROM stock_movement sm
JOIN product p USING (user_id, product_id)
GROUP BY sm.user_id, sm.product_id, p.sku, p.name, p.unit;

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
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP VIEW IF EXISTS product_financials_view;
DROP VIEW IF EXISTS product_stock_view;

DROP TABLE IF EXISTS chat_message;
DROP TABLE IF EXISTS stock_movement;
DROP TABLE IF EXISTS sales_order;
DROP TABLE IF EXISTS purchase_order;
DROP INDEX IF EXISTS product_user_sku_unique;
DROP TABLE IF EXISTS product;

DROP SEQUENCE IF EXISTS chat_message_id_seq;
DROP SEQUENCE IF EXISTS stock_movement_id_seq;
DROP SEQUENCE IF EXISTS sales_order_id_seq;
DROP SEQUENCE IF EXISTS purchase_order_id_seq;
DROP SEQUENCE IF EXISTS product_id_seq;

DROP TYPE IF EXISTS chat_message_role;
DROP TYPE IF EXISTS stock_movement_source;
DROP TYPE IF EXISTS product_unit;

DROP FUNCTION IF EXISTS enforce_stock_movement_product_owner();
DROP FUNCTION IF EXISTS enforce_sales_order_product_owner();
DROP FUNCTION IF EXISTS enforce_purchase_order_product_owner();
-- +goose StatementEnd
