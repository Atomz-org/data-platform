-- source extract for adv_above_store_average (PII columns excluded by the MDL projection)
select order_id, customer_id, location_id, location_name, ordered_at, order_total, count_order_items, is_food_order, is_drink_order, store_avg_order_total, amount_above_average, pct_above_average
from main_marts.adv_above_store_average
