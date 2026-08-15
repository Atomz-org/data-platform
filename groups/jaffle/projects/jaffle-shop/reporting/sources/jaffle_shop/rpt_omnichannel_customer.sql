-- source extract for rpt_omnichannel_customer (PII columns excluded by the MDL projection)
select customer_id, stores_visited, store_engagement_tier, total_orders, total_spend, first_order_date, last_order_date, avg_order_value, orders_per_store
from main_marts.rpt_omnichannel_customer
