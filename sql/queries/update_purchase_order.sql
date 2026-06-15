UPDATE purchase_order
SET quantity = %s, total_cost = %s
WHERE user_id = %s AND purchase_order_id = %s
RETURNING purchase_order_id, quantity, total_cost;
