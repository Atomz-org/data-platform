-- source extract for fct_ingredient_usage (PII columns excluded by the MDL projection)
select order_date, ingredient_id, ingredient_name, ingredient_category, is_perishable, is_allergen, quantity_unit, total_quantity_used, order_item_count, rolling_7d_avg_usage
from main_marts.fct_ingredient_usage
