-- source extract for prod_recipe_yield_analysis (PII columns excluded by the MDL projection)
select product_id, ingredient_id, total_products_sold, expected_ingredient_usage, actual_ingredient_usage, yield_ratio, yield_status
from main_marts.prod_recipe_yield_analysis
