-- source extract for int_menu_breadth_by_store (PII columns excluded by the MDL projection)
select location_id, distinct_products_sold, product_diversity_ratio, location_name, total_items_sold, total_orders
from main_marts.int_menu_breadth_by_store
