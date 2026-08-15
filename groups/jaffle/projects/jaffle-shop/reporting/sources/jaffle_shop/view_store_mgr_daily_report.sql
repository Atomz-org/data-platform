-- source extract for view_store_mgr_daily_report (PII columns excluded by the MDL projection)
select location_id, order_date, daily_revenue, order_count, avg_order_value, labor_cost, labor_hours, waste_cost, labor_cost_pct, waste_pct, day_assessment
from main_marts.view_store_mgr_daily_report
