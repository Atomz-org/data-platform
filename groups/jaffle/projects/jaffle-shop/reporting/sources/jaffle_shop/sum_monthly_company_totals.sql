-- source extract for sum_monthly_company_totals (PII columns excluded by the MDL projection)
select month_start, monthly_revenue, total_orders, avg_order_value, monthly_labor_cost, total_labor_hours, monthly_waste_cost, operating_income_proxy, prior_month_revenue, mom_revenue_change_pct
from main_marts.sum_monthly_company_totals
