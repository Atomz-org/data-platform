-- source extract for trend_food_vs_beverage_mix (PII columns excluded by the MDL projection)
select sale_date, food_revenue, beverage_revenue, total_revenue, food_pct, beverage_pct, food_pct_7d_ma, food_pct_28d_ma, food_pct_last_week
from main_marts.trend_food_vs_beverage_mix
