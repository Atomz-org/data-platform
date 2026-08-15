-- source extract for geo_cross_store_shopping (PII columns excluded by the MDL projection)
select customer_id, distinct_stores, total_orders, first_order_at, last_order_at, avg_orders_per_store, shopping_pattern
from main_marts.geo_cross_store_shopping
