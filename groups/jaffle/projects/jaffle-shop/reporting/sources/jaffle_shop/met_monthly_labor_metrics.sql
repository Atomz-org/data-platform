-- source extract for met_monthly_labor_metrics (PII columns excluded by the MDL projection)
select month_start, location_id, mom_labor_cost_change, store_name, monthly_labor_hours, monthly_labor_cost, avg_daily_employees, monthly_orders, monthly_revenue, orders_per_labor_hour, labor_cost_pct_of_revenue, prev_month_labor_cost
from main_marts.met_monthly_labor_metrics
