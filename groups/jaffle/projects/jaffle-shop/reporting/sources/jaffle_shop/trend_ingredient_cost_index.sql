-- source extract for trend_ingredient_cost_index (PII columns excluded by the MDL projection)
select price_month, avg_ingredient_cost, ingredients_tracked, cost_index, prev_month_cost, mom_change_pct, cost_trend
from main_marts.trend_ingredient_cost_index
