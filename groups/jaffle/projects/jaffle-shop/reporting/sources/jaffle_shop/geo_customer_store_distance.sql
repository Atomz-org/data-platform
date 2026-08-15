-- source extract for geo_customer_store_distance (PII columns excluded by the MDL projection)
select customer_id, customer_name, store_id, store_name, store_rank, store_affinity, order_count, total_spend, first_order_at, last_order_at, total_orders_all_stores, stores_visited, pct_orders_at_store
from main_marts.geo_customer_store_distance
