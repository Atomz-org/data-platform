-- source extract for int_store_daily_summary (PII columns excluded by the MDL projection)
select location_id, order_date, order_count, daily_revenue, labor_hours, revenue_per_labor_hour, waste_cost, waste_as_pct_of_revenue, unique_customers, avg_order_value, labor_cost, employees_on_duty, orders_per_labor_hour, waste_events, units_wasted
from main_marts.int_store_daily_summary
