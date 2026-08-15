-- source extract for order_items (PII columns excluded by the MDL projection)
select order_item_id, order_id, product_id, ordered_at, product_name, product_price, is_food_item, is_drink_item, supply_cost
from main_marts.order_items
