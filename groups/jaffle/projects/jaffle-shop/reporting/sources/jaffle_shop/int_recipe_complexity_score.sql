-- source extract for int_recipe_complexity_score (PII columns excluded by the MDL projection)
select recipe_id, complexity_score, complexity_tier, ingredient_count, distinct_ingredients, total_quantity_units, ingredient_count_score, quantity_complexity_score
from main_marts.int_recipe_complexity_score
