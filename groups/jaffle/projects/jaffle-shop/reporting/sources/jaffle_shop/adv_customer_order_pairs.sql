-- source extract for adv_customer_order_pairs (PII columns excluded by the MDL projection)
select order_id, customer_id, customer_order_number, ordered_at, order_total, count_order_items, location_id, prev_order_id, prev_ordered_at, prev_order_total, prev_count_order_items, prev_location_id, days_between_orders, amount_change_pct, did_store_change, did_product_mix_change
from main_marts.adv_customer_order_pairs
