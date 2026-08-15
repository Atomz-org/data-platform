-- source extract for wide_daily_business_summary (PII columns excluded by the MDL projection)
select summary_date, total_revenue, total_orders, avg_order_value, total_active_customers, total_new_customers, total_labor_cost, total_labor_hours, total_waste_cost, total_waste_events, labor_cost_pct, waste_cost_pct
from main_marts.wide_daily_business_summary
