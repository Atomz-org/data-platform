-- source extract for sum_weekly_company_totals (PII columns excluded by the MDL projection)
select week_start, total_revenue, total_orders, avg_order_value, total_labor_cost, labor_cost_pct, prior_week_revenue, wow_revenue_change_pct
from main_marts.sum_weekly_company_totals
