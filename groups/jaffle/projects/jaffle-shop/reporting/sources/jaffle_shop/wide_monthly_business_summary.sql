-- source extract for wide_monthly_business_summary (PII columns excluded by the MDL projection)
select summary_month, monthly_revenue, monthly_orders, avg_order_value, total_new_customers, monthly_labor_cost, monthly_waste_cost, labor_cost_pct, waste_cost_pct, prev_month_revenue, mom_revenue_growth_pct, yoy_month_revenue, yoy_revenue_growth_pct
from main_marts.wide_monthly_business_summary
