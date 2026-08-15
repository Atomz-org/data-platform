-- source extract for rpt_recipe_cost_variance (PII columns excluded by the MDL projection)
select recipe_id, recipe_name, menu_item_id, is_active_recipe, ingredient_count, calculated_total_cost, baseline_total_cost, cost_variance, cost_variance_pct, max_ingredient_cost, min_ingredient_cost, ingredient_cost_spread, variance_status
from main_marts.rpt_recipe_cost_variance
