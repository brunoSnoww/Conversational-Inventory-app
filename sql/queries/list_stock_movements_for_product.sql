SELECT sm.stock_movement_id, sm.product_id, p.sku, sm.quantity_delta,
       sm.unit_cost, sm.source, sm.source_id, sm.created_at
FROM stock_movement sm
JOIN product p ON p.product_id = sm.product_id AND p.user_id = sm.user_id
WHERE sm.user_id = %s AND sm.product_id = %s
ORDER BY sm.stock_movement_id DESC;
