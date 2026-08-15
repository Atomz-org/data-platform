-- source extract for prod_product_cannibalization (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, new_product_launch_date, pre_launch_qty, post_launch_qty, avg_daily_pre, avg_daily_post, sales_change_pct
from main_marts.prod_product_cannibalization
