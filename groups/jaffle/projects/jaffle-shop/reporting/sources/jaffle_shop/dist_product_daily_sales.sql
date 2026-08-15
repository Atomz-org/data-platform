-- source extract for dist_product_daily_sales (PII columns excluded by the MDL projection)
select product_id, mean_daily_qty, median_daily_qty, p75_daily_qty, p90_daily_qty, min_daily_qty, max_daily_qty, active_days
from main_marts.dist_product_daily_sales
