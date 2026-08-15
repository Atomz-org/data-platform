-- source extract for int_revenue_per_customer_monthly (PII columns excluded by the MDL projection)
select customer_id, revenue_month, total_revenue, customer_name, order_count, avg_order_value
from main_marts.int_revenue_per_customer_monthly
