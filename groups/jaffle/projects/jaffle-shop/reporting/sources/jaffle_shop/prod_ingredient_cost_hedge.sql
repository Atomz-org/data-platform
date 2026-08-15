-- source extract for prod_ingredient_cost_hedge (PII columns excluded by the MDL projection)
select ingredient_id, ingredient_name, ingredient_category, mean_cost, cost_range, volatility_ratio, avg_monthly_change, months_with_5pct_increase, hedge_recommendation
from main_marts.prod_ingredient_cost_hedge
