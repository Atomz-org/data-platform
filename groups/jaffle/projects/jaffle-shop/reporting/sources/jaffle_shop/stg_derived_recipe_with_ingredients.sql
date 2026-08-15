-- source extract for stg_derived_recipe_with_ingredients (PII columns excluded by the MDL projection)
select recipe_id, menu_item_id, recipe_name, ingredient_id, ingredient_name, ingredient_quantity, quantity_unit
from main_marts.stg_derived_recipe_with_ingredients
