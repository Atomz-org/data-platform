-- source extract for stg_derived_menu_item_with_category (PII columns excluded by the MDL projection)
select menu_item_id, product_id, menu_item_name, menu_category_id, category_name, menu_item_price, is_available
from main_marts.stg_derived_menu_item_with_category
