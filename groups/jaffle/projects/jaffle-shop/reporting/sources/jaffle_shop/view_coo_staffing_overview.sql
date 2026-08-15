-- source extract for view_coo_staffing_overview (PII columns excluded by the MDL projection)
select location_id, report_week, total_weekly_scheduled_hours, total_weekly_orders, avg_orders_per_staff, active_employees, hours_variance, staffing_status
from main_marts.view_coo_staffing_overview
