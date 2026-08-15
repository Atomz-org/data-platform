-- source extract for dim_menu_categories (PII columns excluded by the MDL projection)
select menu_category_id, parent_category_id, category_name, category_description, category_display_order, category_depth, is_active_category, parent_category_name
from main_marts.dim_menu_categories
