-- source extract for int_store_revenue_costs (PII columns excluded by the MDL projection)
select store_id, report_month, net_operating_income, operating_margin_pct, location_id, month_start, monthly_revenue, monthly_expenses, monthly_labor_cost, monthly_hours_worked, unique_employees
from main_marts.int_store_revenue_costs
