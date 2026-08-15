-- source extract for prod_recipe_simplification (PII columns excluded by the MDL projection)
select recipe_id, recipe_name, menu_item_id, ingredient_count, gross_margin, gross_margin_pct, simplification_recommendation, estimated_savings_per_unit
from main_marts.prod_recipe_simplification
