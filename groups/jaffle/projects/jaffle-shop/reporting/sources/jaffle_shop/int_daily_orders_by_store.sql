-- source extract for int_daily_orders_by_store (PII columns excluded by the MDL projection)
select order_date, location_id, location_name, order_count, unique_customers, total_revenue, avg_order_value, total_subtotal
from main_marts.int_daily_orders_by_store
