DELETE FROM sales_order
WHERE user_id = %s AND sales_order_id = %s
RETURNING sales_order_id;
