-- source extract for prod_food_vs_beverage_trend (PII columns excluded by the MDL projection)
select sale_month, product_type, monthly_qty, monthly_revenue, total_revenue, revenue_share_pct, prev_month_revenue, mom_growth_pct
from main_marts.prod_food_vs_beverage_trend
