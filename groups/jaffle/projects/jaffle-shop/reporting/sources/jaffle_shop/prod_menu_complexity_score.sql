-- source extract for prod_menu_complexity_score (PII columns excluded by the MDL projection)
select menu_item_id, menu_item_name, category_name, ingredient_count, ingredient_category_count, total_menu_items, total_categories, item_complexity, complexity_score
from main_marts.prod_menu_complexity_score
