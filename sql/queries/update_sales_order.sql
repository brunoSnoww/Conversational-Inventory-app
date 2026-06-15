UPDATE sales_order
SET quantity = %s, unit_price = %s
WHERE user_id = %s AND sales_order_id = %s
RETURNING sales_order_id, quantity, unit_price;
