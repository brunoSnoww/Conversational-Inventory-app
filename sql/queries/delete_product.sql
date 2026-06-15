DELETE FROM product
WHERE user_id = %s AND product_id = %s
RETURNING product_id;
