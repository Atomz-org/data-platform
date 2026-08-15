-- source extract for adv_latest_event_per_customer (PII columns excluded by the MDL projection)
select customer_id, customer_name, order_id, ordered_at, order_total, count_order_items, is_food_order, is_drink_order, location_id, location_name, recency_rank
from main_marts.adv_latest_event_per_customer
