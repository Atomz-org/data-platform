-- source extract for met_daily_labor_metrics (PII columns excluded by the MDL projection)
select work_date, location_id, orders_per_labor_hour, labor_cost_pct_of_revenue, store_name, total_labor_hours, total_labor_cost, employee_count, order_count, daily_revenue, revenue_per_labor_hour
from main_marts.met_daily_labor_metrics
