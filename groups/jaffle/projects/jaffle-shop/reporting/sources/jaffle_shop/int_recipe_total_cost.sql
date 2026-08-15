-- source extract for int_recipe_total_cost (PII columns excluded by the MDL projection)
select recipe_id, ingredient_count, total_ingredient_cost, highest_ingredient_cost, lowest_ingredient_cost
from main_marts.int_recipe_total_cost
