-- source extract for dim_recipes (PII columns excluded by the MDL projection)
select recipe_id, menu_item_id, recipe_name, recipe_description, serving_size, is_active_recipe, created_date, updated_date, ingredient_count, total_ingredient_cost, highest_ingredient_cost, lowest_ingredient_cost, cost_per_serving
from main_marts.dim_recipes
