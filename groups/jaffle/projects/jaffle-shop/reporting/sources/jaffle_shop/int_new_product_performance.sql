-- source extract for int_new_product_performance (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, launch_date, days_on_market, units_sold_30d, revenue_30d, avg_daily_units_30d, units_sold_60d, revenue_60d, avg_daily_units_60d, units_sold_90d, revenue_90d, avg_daily_units_90d, active_days_30d, active_days_60d, active_days_90d, total_units_sold, total_revenue
from main_marts.int_new_product_performance
