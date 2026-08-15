-- source extract for view_store_mgr_labor_summary (PII columns excluded by the MDL projection)
select location_id, work_date, total_labor_hours, total_labor_cost, employee_count, orders_per_labor_hour, labor_cost_pct_of_revenue, avg_hourly_cost, labor_cost_status
from main_marts.view_store_mgr_labor_summary
