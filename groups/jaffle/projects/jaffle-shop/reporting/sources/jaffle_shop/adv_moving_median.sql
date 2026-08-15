-- source extract for adv_moving_median (PII columns excluded by the MDL projection)
select order_date, location_id, location_name, daily_revenue, order_count, median_revenue_7d, revenue_vs_median, pct_above_median
from main_marts.adv_moving_median
