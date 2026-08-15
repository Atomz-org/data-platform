-- source extract for mkt_customer_lifecycle_stage (PII columns excluded by the MDL projection)
select customer_id, total_orders, days_since_last_order, first_order_at, last_order_at, lifetime_spend, rfm_segment, historical_lapses, lifecycle_stage
from main_marts.mkt_customer_lifecycle_stage
