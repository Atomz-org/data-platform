-- source extract for met_weekly_labor_metrics (PII columns excluded by the MDL projection)
select week_start, location_id, store_name, weekly_labor_hours, weekly_labor_cost, avg_daily_employees, weekly_orders, weekly_revenue, orders_per_labor_hour, labor_cost_pct_of_revenue
from main_marts.met_weekly_labor_metrics
