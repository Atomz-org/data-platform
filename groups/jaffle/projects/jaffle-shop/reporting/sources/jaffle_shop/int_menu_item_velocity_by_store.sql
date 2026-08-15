-- source extract for int_menu_item_velocity_by_store (PII columns excluded by the MDL projection)
select product_id, location_id, daily_sales_velocity, velocity_tier, product_name, product_type, location_name, total_units_sold, total_orders, first_sold_date, last_sold_date
from main_marts.int_menu_item_velocity_by_store
