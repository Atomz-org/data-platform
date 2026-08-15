-- source extract for inc_met_daily_orders (PII columns excluded by the MDL projection)
select order_metric_key, store_id, order_date, total_orders, unique_customers, total_order_value, avg_order_value
from main_marts.inc_met_daily_orders
