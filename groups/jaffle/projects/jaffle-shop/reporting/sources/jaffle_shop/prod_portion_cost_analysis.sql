-- source extract for prod_portion_cost_analysis (PII columns excluded by the MDL projection)
select menu_item_id, menu_item_name, menu_item_price, recipe_id, ingredient_id, ingredient_name, ingredient_line_cost, total_recipe_cost, ingredient_pct_of_price, cost_rank
from main_marts.prod_portion_cost_analysis
