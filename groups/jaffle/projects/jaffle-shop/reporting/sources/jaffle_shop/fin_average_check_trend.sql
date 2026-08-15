-- source extract for fin_average_check_trend (PII columns excluded by the MDL projection)
select location_id, store_name, order_week, weekly_orders, avg_check_size, min_check_size, max_check_size, avg_check_4_week_moving_avg, check_size_growth_pct_4w
from main_marts.fin_average_check_trend
