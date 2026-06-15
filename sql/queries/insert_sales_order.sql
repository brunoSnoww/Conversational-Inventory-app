INSERT INTO sales_order (user_id, product_id, quantity, unit_price, guid)
VALUES (%s, %s, %s, %s, %s)
RETURNING sales_order_id, quantity, unit_price;
