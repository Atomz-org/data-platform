-- source extract for int_customer_status_monthly (PII columns excluded by the MDL projection)
select month_start, customer_id, customer_status, days_since_last_order, lifetime_orders, last_order_date
from main_marts.int_customer_status_monthly
