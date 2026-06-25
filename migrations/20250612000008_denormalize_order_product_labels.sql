-- +goose Up
-- +goose StatementBegin
-- Denormalize product labels onto orders so PowerSync clients avoid JOIN reads (Octopus pattern).

ALTER TABLE purchase_order
    ADD COLUMN product_sku TEXT NOT NULL DEFAULT '',
    ADD COLUMN product_name TEXT NOT NULL DEFAULT '';

ALTER TABLE sales_order
    ADD COLUMN product_sku TEXT NOT NULL DEFAULT '',
    ADD COLUMN product_name TEXT NOT NULL DEFAULT '';

CREATE FUNCTION sync_order_product_denorm() RETURNS trigger AS $$
BEGIN
    SELECT sku, name
    INTO NEW.product_sku, NEW.product_name
    FROM product
    WHERE product_id = NEW.product_id;

    IF NEW.product_sku IS NULL THEN
        RAISE EXCEPTION 'product_id % not found for order denormalization', NEW.product_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER purchase_order_product_denorm_trigger
    BEFORE INSERT OR UPDATE OF product_id ON purchase_order
    FOR EACH ROW EXECUTE PROCEDURE sync_order_product_denorm();

CREATE TRIGGER sales_order_product_denorm_trigger
    BEFORE INSERT OR UPDATE OF product_id ON sales_order
    FOR EACH ROW EXECUTE PROCEDURE sync_order_product_denorm();

CREATE FUNCTION refresh_order_product_denorm() RETURNS trigger AS $$
BEGIN
    UPDATE purchase_order
    SET product_sku = NEW.sku, product_name = NEW.name
    WHERE product_id = NEW.product_id;

    UPDATE sales_order
    SET product_sku = NEW.sku, product_name = NEW.name
    WHERE product_id = NEW.product_id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER product_order_denorm_trigger
    AFTER UPDATE OF sku, name ON product
    FOR EACH ROW EXECUTE PROCEDURE refresh_order_product_denorm();

ALTER TABLE stock_movement
    ADD COLUMN product_sku TEXT NOT NULL DEFAULT '';

CREATE FUNCTION sync_stock_movement_product_denorm() RETURNS trigger AS $$
BEGIN
    SELECT sku
    INTO NEW.product_sku
    FROM product
    WHERE product_id = NEW.product_id;

    IF NEW.product_sku IS NULL THEN
        RAISE EXCEPTION 'product_id % not found for stock movement denormalization', NEW.product_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER stock_movement_product_denorm_trigger
    BEFORE INSERT OR UPDATE OF product_id ON stock_movement
    FOR EACH ROW EXECUTE PROCEDURE sync_stock_movement_product_denorm();

CREATE FUNCTION refresh_stock_movement_product_denorm() RETURNS trigger AS $$
BEGIN
    UPDATE stock_movement
    SET product_sku = NEW.sku
    WHERE product_id = NEW.product_id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER product_stock_movement_denorm_trigger
    AFTER UPDATE OF sku ON product
    FOR EACH ROW EXECUTE PROCEDURE refresh_stock_movement_product_denorm();

UPDATE stock_movement sm
SET product_sku = p.sku
FROM product p
WHERE p.product_id = sm.product_id;

ALTER TABLE stock_movement
    ALTER COLUMN product_sku DROP DEFAULT;

UPDATE purchase_order po
SET product_sku = p.sku, product_name = p.name
FROM product p
WHERE p.product_id = po.product_id;

UPDATE sales_order so
SET product_sku = p.sku, product_name = p.name
FROM product p
WHERE p.product_id = so.product_id;

ALTER TABLE purchase_order
    ALTER COLUMN product_sku DROP DEFAULT,
    ALTER COLUMN product_name DROP DEFAULT;

ALTER TABLE sales_order
    ALTER COLUMN product_sku DROP DEFAULT,
    ALTER COLUMN product_name DROP DEFAULT;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP TRIGGER IF EXISTS product_stock_movement_denorm_trigger ON product;
DROP FUNCTION IF EXISTS refresh_stock_movement_product_denorm();
DROP TRIGGER IF EXISTS stock_movement_product_denorm_trigger ON stock_movement;
DROP FUNCTION IF EXISTS sync_stock_movement_product_denorm();

ALTER TABLE stock_movement
    DROP COLUMN IF EXISTS product_sku;

DROP TRIGGER IF EXISTS product_order_denorm_trigger ON product;
DROP FUNCTION IF EXISTS refresh_order_product_denorm();

DROP TRIGGER IF EXISTS sales_order_product_denorm_trigger ON sales_order;
DROP TRIGGER IF EXISTS purchase_order_product_denorm_trigger ON purchase_order;
DROP FUNCTION IF EXISTS sync_order_product_denorm();

ALTER TABLE sales_order
    DROP COLUMN IF EXISTS product_sku,
    DROP COLUMN IF EXISTS product_name;

ALTER TABLE purchase_order
    DROP COLUMN IF EXISTS product_sku,
    DROP COLUMN IF EXISTS product_name;
-- +goose StatementEnd
