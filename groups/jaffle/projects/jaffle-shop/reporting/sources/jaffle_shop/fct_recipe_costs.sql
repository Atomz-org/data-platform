-- source extract for fct_recipe_costs (PII columns excluded by the MDL projection)
select recipe_ingredient_id, recipe_id, recipe_name, menu_item_id, is_active_recipe, ingredient_id, ingredient_name, ingredient_category, quantity, quantity_unit, ingredient_unit_cost, ingredient_line_cost, cost_share_pct
from main_marts.fct_recipe_costs
