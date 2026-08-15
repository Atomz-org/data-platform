-- source extract for int_menu_item_margin (PII columns excluded by the MDL projection)
select menu_item_id, menu_item_name, menu_item_price, total_ingredient_cost, gross_margin, gross_margin_pct, category_name, product_type, is_available, recipe_id, ingredient_count
from main_marts.int_menu_item_margin
