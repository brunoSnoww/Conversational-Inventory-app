DELETE FROM purchase_order
WHERE user_id = %s AND purchase_order_id = %s
RETURNING purchase_order_id;
