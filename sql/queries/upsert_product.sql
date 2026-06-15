INSERT INTO product (user_id, name, description, sku, unit)
VALUES (%s, %s, %s, %s, %s::product_unit)
ON CONFLICT (user_id, lower(sku))
DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    unit = EXCLUDED.unit,
    updated_at = now()
RETURNING product_id, sku, name, unit, description;
