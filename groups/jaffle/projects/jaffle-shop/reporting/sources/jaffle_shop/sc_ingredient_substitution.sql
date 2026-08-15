-- source extract for sc_ingredient_substitution (PII columns excluded by the MDL projection)
select original_id, original_name, ingredient_category, substitute_id, substitute_name, same_unit, perishability_match, substitute_is_allergen, substitute_recipe_usage, substitution_fit
from main_marts.sc_ingredient_substitution
