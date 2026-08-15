-- source extract for sum_daily_company_totals (PII columns excluded by the MDL projection)
select report_date, total_revenue, total_orders, avg_order_value, total_labor_cost, total_labor_hours, total_waste_cost, labor_cost_pct, waste_cost_pct
from main_marts.sum_daily_company_totals
