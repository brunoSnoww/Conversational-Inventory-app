SELECT product_id, user_id, sku, name, unit, description
FROM product
WHERE user_id = %s AND product_id = %s;
