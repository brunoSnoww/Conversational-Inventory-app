SELECT sales_order_id, quantity, unit_price
FROM sales_order
WHERE user_id = %s AND guid = %s;
