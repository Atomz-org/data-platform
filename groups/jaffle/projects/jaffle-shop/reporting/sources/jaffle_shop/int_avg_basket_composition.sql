-- source extract for int_avg_basket_composition (PII columns excluded by the MDL projection)
select avg_items_per_order, avg_basket_value, single_item_orders, large_basket_orders, avg_distinct_products_per_order, avg_categories_per_order, min_items_per_order, max_items_per_order, small_basket_orders, total_orders
from main_marts.int_avg_basket_composition
