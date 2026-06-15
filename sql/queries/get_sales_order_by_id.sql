SELECT so.sales_order_id, so.product_id, so.quantity, so.unit_price, p.sku
FROM sales_order so
JOIN product p ON p.product_id = so.product_id AND p.user_id = so.user_id
WHERE so.user_id = %s AND so.sales_order_id = %s;
