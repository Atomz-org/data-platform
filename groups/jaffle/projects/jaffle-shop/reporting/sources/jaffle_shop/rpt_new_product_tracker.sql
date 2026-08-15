-- source extract for rpt_new_product_tracker (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, launch_date, days_on_market, units_sold_30d, revenue_30d, avg_daily_units_30d, units_sold_60d, revenue_60d, avg_daily_units_60d, units_sold_90d, revenue_90d, avg_daily_units_90d, total_units_sold, total_revenue, pct_vs_benchmark_30d, pct_vs_benchmark_90d, velocity_change_30_to_60d, launch_classification
from main_marts.rpt_new_product_tracker
