-- source extract for int_store_metrics_weekly (PII columns excluded by the MDL projection)
select week_start, location_id, location_name, order_count, unique_customers, total_revenue, avg_ticket_size, total_subtotal, total_tax, min_order_value, max_order_value
from main_marts.int_store_metrics_weekly
