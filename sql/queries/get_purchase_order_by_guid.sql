SELECT purchase_order_id, quantity, total_cost
FROM purchase_order
WHERE user_id = %s AND guid = %s;
