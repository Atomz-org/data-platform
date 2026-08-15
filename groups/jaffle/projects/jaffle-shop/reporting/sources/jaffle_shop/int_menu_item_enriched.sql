-- source extract for int_menu_item_enriched (PII columns excluded by the MDL projection)
select menu_item_id, product_id, menu_category_id, menu_item_name, menu_item_price, category_name, product_type, calories, sodium_mg, protein_g, menu_item_description, menu_item_size, display_order, is_available, is_combo, is_seasonal, parent_category_id, category_depth, product_name, is_food_item, is_drink_item, total_fat_g, total_sugars_g, caffeine_mg, serving_size_description
from main_marts.int_menu_item_enriched
