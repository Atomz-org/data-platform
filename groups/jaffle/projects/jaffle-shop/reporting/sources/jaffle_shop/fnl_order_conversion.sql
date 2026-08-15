-- source extract for fnl_order_conversion (PII columns excluded by the MDL projection)
select order_month, total_orders_placed, orders_with_revenue, revenue_capture_rate_pct, fulfillment_rate_pct, orders_fulfilled, unique_customers, orders_per_customer
from main_marts.fnl_order_conversion
