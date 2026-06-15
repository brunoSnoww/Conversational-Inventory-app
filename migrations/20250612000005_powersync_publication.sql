-- +goose Up
-- Logical replication publication for PowerSync.
-- Do NOT publish app_user (password_hash). Views are not published — clients sync base tables.

CREATE PUBLICATION powersync FOR TABLE
    product,
    purchase_order,
    sales_order,
    stock_movement,
    chat_message;

-- +goose Down
DROP PUBLICATION IF EXISTS powersync;
