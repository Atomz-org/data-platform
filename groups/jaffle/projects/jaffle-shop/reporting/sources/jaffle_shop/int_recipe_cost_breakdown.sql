-- source extract for int_recipe_cost_breakdown (PII columns excluded by the MDL projection)
select recipe_ingredient_id, recipe_id, ingredient_id, ingredient_name, ingredient_category, quantity, quantity_unit, ingredient_unit_cost, ingredient_line_cost
from main_marts.int_recipe_cost_breakdown
