INSERT INTO purchase_order (user_id, product_id, quantity, total_cost, guid)
VALUES (%s, %s, %s, %s, %s)
RETURNING purchase_order_id, quantity, total_cost;
