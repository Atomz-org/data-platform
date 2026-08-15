-- source extract for int_peak_hour_analysis (PII columns excluded by the MDL projection)
select store_id, order_hour, hour_classification, store_total_peak_hours, avg_orders_per_hour, avg_revenue_per_hour, hour_share_of_total_pct, hour_rank_by_volume, store_avg_orders_per_hour, store_peak_hours_share_pct
from main_marts.int_peak_hour_analysis
