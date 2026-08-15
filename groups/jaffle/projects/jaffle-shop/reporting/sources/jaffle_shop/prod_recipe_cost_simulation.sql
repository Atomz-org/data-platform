-- source extract for prod_recipe_cost_simulation (PII columns excluded by the MDL projection)
select recipe_id, recipe_name, menu_item_id, menu_item_price, current_margin, current_margin_pct, current_total_cost, simulated_cost_10pct_increase, simulated_margin_10pct, simulated_margin_pct_10pct, additional_cost_from_increase, cost_impact_severity
from main_marts.prod_recipe_cost_simulation
