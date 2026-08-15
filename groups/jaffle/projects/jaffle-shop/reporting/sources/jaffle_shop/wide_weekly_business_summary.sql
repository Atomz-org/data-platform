-- source extract for wide_weekly_business_summary (PII columns excluded by the MDL projection)
select summary_week, weekly_revenue, weekly_orders, avg_order_value, total_active_customers, total_new_customers, weekly_labor_cost, weekly_labor_hours, weekly_waste_cost, weekly_waste_events, labor_cost_pct, waste_cost_pct, days_in_week
from main_marts.wide_weekly_business_summary
