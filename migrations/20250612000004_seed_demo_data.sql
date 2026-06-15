-- +goose Up
-- +goose StatementBegin
-- Demo seed — Sunrise Pantry Co. (F&B CPG)
-- Login: demo@inventory.local / password123
--
-- Product A (SKU A): historical book — bought 100 @ $100, sold 100 @ $10 → profit $900, stock 0
-- CB-01: Craft Beer IPA 12oz — 400 units on hand ($2/unit) — chat PO demo adds 100 @ $200
-- OL-01: Olive Oil EVOO 750mL — 24 bottles on hand ($3/unit) — extra dashboard row
-- No chat messages — clean slate for demo recording

INSERT INTO app_user (email, password_hash)
VALUES (
    'demo@inventory.local',
    'pbkdf2_sha256$600000$vlZfUaQYupmb8KzMSD8NOw$ZYcFxXvrEzN8jkPK6FV3cS710zrb2XdTwcSdUNCoZRk='
)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Product A — closed scenario (backend tests expect profit $900, stock 0)
-- ---------------------------------------------------------------------------
WITH u AS (
    SELECT user_id FROM app_user WHERE lower(email) = lower('demo@inventory.local')
),
p AS (
    INSERT INTO product (user_id, name, description, sku, unit)
    SELECT user_id,
           'Product A',
           'Starter SKU — full buy/sell cycle already booked',
           'A',
           'unit'::product_unit
    FROM u
    ON CONFLICT (user_id, lower(sku))
    DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
    RETURNING user_id, product_id
),
po AS (
    INSERT INTO purchase_order (user_id, product_id, quantity, total_cost, guid)
    SELECT p.user_id, p.product_id, 100, 100.00, '11111111-1111-4111-8111-111111111111'::uuid
    FROM p
    ON CONFLICT (user_id, guid) DO NOTHING
    RETURNING user_id, product_id, purchase_order_id
)
INSERT INTO stock_movement (user_id, product_id, quantity_delta, unit_cost, source, source_id)
SELECT po.user_id, po.product_id, 100, 1.00, 'PURCHASE_ORDER'::stock_movement_source, po.purchase_order_id
FROM po
WHERE NOT EXISTS (
    SELECT 1 FROM stock_movement sm
    WHERE sm.source = 'PURCHASE_ORDER' AND sm.source_id = po.purchase_order_id
);

WITH u AS (
    SELECT user_id FROM app_user WHERE lower(email) = lower('demo@inventory.local')
),
p AS (
    SELECT product_id, user_id
    FROM product
    WHERE user_id = (SELECT user_id FROM u) AND lower(sku) = 'a'
),
so AS (
    INSERT INTO sales_order (user_id, product_id, quantity, unit_price, guid)
    SELECT p.user_id, p.product_id, 100, 10.00, '22222222-2222-4222-8222-222222222222'::uuid
    FROM p
    ON CONFLICT (user_id, guid) DO NOTHING
    RETURNING user_id, product_id, sales_order_id
)
INSERT INTO stock_movement (user_id, product_id, quantity_delta, source, source_id)
SELECT so.user_id, so.product_id, -100, 'SALES_ORDER'::stock_movement_source, so.sales_order_id
FROM so
WHERE NOT EXISTS (
    SELECT 1 FROM stock_movement sm
    WHERE sm.source = 'SALES_ORDER' AND sm.source_id = so.sales_order_id
);

-- ---------------------------------------------------------------------------
-- CB-01 — hero SKU for live chat PO demo (400 units @ $2/unit)
-- ---------------------------------------------------------------------------
WITH u AS (
    SELECT user_id FROM app_user WHERE lower(email) = lower('demo@inventory.local')
),
p AS (
    INSERT INTO product (user_id, name, description, sku, unit)
    SELECT user_id,
           'Craft Beer — IPA 12oz',
           'Flagship SKU — use chat to add a purchase order',
           'CB-01',
           'unit'::product_unit
    FROM u
    ON CONFLICT (user_id, lower(sku))
    DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
    RETURNING user_id, product_id
),
po AS (
    INSERT INTO purchase_order (user_id, product_id, quantity, total_cost, guid)
    SELECT p.user_id, p.product_id, 400, 800.00, '33333333-3333-4333-8333-333333333333'::uuid
    FROM p
    ON CONFLICT (user_id, guid) DO NOTHING
    RETURNING user_id, product_id, purchase_order_id
)
INSERT INTO stock_movement (user_id, product_id, quantity_delta, unit_cost, source, source_id)
SELECT po.user_id, po.product_id, 400, 2.00, 'PURCHASE_ORDER'::stock_movement_source, po.purchase_order_id
FROM po
WHERE NOT EXISTS (
    SELECT 1 FROM stock_movement sm
    WHERE sm.source = 'PURCHASE_ORDER' AND sm.source_id = po.purchase_order_id
);

-- ---------------------------------------------------------------------------
-- OL-01 — second live SKU on dashboard (24 bottles @ $3/unit)
-- ---------------------------------------------------------------------------
WITH u AS (
    SELECT user_id FROM app_user WHERE lower(email) = lower('demo@inventory.local')
),
p AS (
    INSERT INTO product (user_id, name, description, sku, unit)
    SELECT user_id,
           'Olive Oil — EVOO 750mL',
           'Pantry staple',
           'OL-01',
           'mL'::product_unit
    FROM u
    ON CONFLICT (user_id, lower(sku))
    DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description
    RETURNING user_id, product_id
),
po AS (
    INSERT INTO purchase_order (user_id, product_id, quantity, total_cost, guid)
    SELECT p.user_id, p.product_id, 24, 72.00, '44444444-4444-4444-8444-444444444444'::uuid
    FROM p
    ON CONFLICT (user_id, guid) DO NOTHING
    RETURNING user_id, product_id, purchase_order_id
)
INSERT INTO stock_movement (user_id, product_id, quantity_delta, unit_cost, source, source_id)
SELECT po.user_id, po.product_id, 24, 3.00, 'PURCHASE_ORDER'::stock_movement_source, po.purchase_order_id
FROM po
WHERE NOT EXISTS (
    SELECT 1 FROM stock_movement sm
    WHERE sm.source = 'PURCHASE_ORDER' AND sm.source_id = po.purchase_order_id
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DELETE FROM chat_message
WHERE user_id IN (SELECT user_id FROM app_user WHERE lower(email) = lower('demo@inventory.local'));

DELETE FROM stock_movement
WHERE source_id IN (
    SELECT purchase_order_id FROM purchase_order
    WHERE guid IN (
        '11111111-1111-4111-8111-111111111111'::uuid,
        '33333333-3333-4333-8333-333333333333'::uuid,
        '44444444-4444-4444-8444-444444444444'::uuid
    )
    UNION ALL
    SELECT sales_order_id FROM sales_order
    WHERE guid = '22222222-2222-4222-8222-222222222222'::uuid
);

DELETE FROM sales_order
WHERE guid = '22222222-2222-4222-8222-222222222222'::uuid;

DELETE FROM purchase_order
WHERE guid IN (
    '11111111-1111-4111-8111-111111111111'::uuid,
    '33333333-3333-4333-8333-333333333333'::uuid,
    '44444444-4444-4444-8444-444444444444'::uuid
);

DELETE FROM product
WHERE lower(sku) IN ('a', 'cb-01', 'ol-01')
  AND user_id IN (
      SELECT user_id FROM app_user WHERE lower(email) = lower('demo@inventory.local')
  );

DELETE FROM app_user
WHERE lower(email) = lower('demo@inventory.local');
-- +goose StatementEnd
