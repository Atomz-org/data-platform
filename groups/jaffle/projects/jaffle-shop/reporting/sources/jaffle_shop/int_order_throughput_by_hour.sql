-- source extract for int_order_throughput_by_hour (PII columns excluded by the MDL projection)
select store_id, order_hour, avg_orders_per_hour, hour_share_of_total_pct, avg_revenue_per_hour, days_with_data, peak_orders_in_hour, total_orders_in_hour, store_total_orders
from main_marts.int_order_throughput_by_hour
