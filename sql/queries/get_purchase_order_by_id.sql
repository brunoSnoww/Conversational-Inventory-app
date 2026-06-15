SELECT po.purchase_order_id, po.product_id, po.quantity, po.total_cost, p.sku
FROM purchase_order po
JOIN product p ON p.product_id = po.product_id AND p.user_id = po.user_id
WHERE po.user_id = %s AND po.purchase_order_id = %s;
