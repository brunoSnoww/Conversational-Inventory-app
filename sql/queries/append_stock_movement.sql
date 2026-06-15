INSERT INTO stock_movement (user_id, product_id, quantity_delta, unit_cost, source, source_id)
VALUES (%s, %s, %s, %s, %s::stock_movement_source, %s)
RETURNING stock_movement_id, product_id, quantity_delta, unit_cost, source, source_id, created_at;
