-- source extract for int_revenue_by_customer_segment (PII columns excluded by the MDL projection)
select rfm_segment, revenue_month, segment_revenue, customer_count, segment_orders, avg_revenue_per_customer
from main_marts.int_revenue_by_customer_segment
