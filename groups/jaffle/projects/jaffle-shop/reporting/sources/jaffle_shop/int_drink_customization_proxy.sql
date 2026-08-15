-- source extract for int_drink_customization_proxy (PII columns excluded by the MDL projection)
select menu_category_id, product_count, menu_item_count, variety_level, category_name, product_type, size_variants
from main_marts.int_drink_customization_proxy
