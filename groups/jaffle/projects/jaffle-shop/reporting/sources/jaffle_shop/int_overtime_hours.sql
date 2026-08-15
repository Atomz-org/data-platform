-- source extract for int_overtime_hours (PII columns excluded by the MDL projection)
select employee_id, location_id, week_start, weekly_total_hours, weekly_daily_overtime_hours, weekly_threshold_overtime_hours, total_overtime_hours
from main_marts.int_overtime_hours
