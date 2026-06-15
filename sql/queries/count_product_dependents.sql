WITH ctx AS (
    SELECT %s::bigint AS user_id, %s::bigint AS product_id
)
SELECT
    (SELECT COUNT(*) FROM stock_movement sm JOIN ctx c ON sm.user_id = c.user_id AND sm.product_id = c.product_id) AS movements,
    (SELECT COUNT(*) FROM purchase_order po JOIN ctx c ON po.user_id = c.user_id AND po.product_id = c.product_id) AS purchases,
    (SELECT COUNT(*) FROM sales_order so JOIN ctx c ON so.user_id = c.user_id AND so.product_id = c.product_id) AS sales;
