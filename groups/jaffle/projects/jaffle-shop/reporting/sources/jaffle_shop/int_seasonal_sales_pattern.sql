-- source extract for int_seasonal_sales_pattern (PII columns excluded by the MDL projection)
select product_id, product_name, season_name, promotion_name, is_during_promotion, total_units_sold, total_revenue, avg_daily_units, promotion_start_date, promotion_end_date, active_days
from main_marts.int_seasonal_sales_pattern
