-- source extract for dim_ingredients (PII columns excluded by the MDL projection)
select ingredient_id, ingredient_name, ingredient_category, default_unit, is_perishable, is_allergen, current_unit_cost
from main_marts.dim_ingredients
