-- source extract for products (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, product_description, product_price, is_food_item, is_drink_item
from main_marts.products
