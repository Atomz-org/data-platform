-- source extract for prod_allergen_risk_assessment (PII columns excluded by the MDL projection)
select menu_item_id, menu_item_name, recipe_name, allergen_ingredient_count, total_ingredient_count, allergen_list, allergen_risk_level
from main_marts.prod_allergen_risk_assessment
