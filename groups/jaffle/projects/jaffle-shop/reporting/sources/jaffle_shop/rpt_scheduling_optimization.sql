-- source extract for rpt_scheduling_optimization (PII columns excluded by the MDL projection)
select location_id, location_name, report_week, avg_daily_staff, total_weekly_scheduled_hours, total_weekly_orders, avg_staff_hours_per_order, avg_orders_per_staff, min_daily_staff, max_daily_staff, staffing_assessment
from main_marts.rpt_scheduling_optimization
