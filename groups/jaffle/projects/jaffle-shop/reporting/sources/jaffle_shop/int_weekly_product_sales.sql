-- source extract for int_weekly_product_sales (PII columns excluded by the MDL projection)
select week_start, product_id, product_name, units_sold, weekly_revenue, avg_daily_units, product_type, order_count, active_days_in_week
from main_marts.int_weekly_product_sales
