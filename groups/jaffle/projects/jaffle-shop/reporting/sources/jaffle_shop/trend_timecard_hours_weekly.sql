-- source extract for trend_timecard_hours_weekly (PII columns excluded by the MDL projection)
select work_week, location_id, total_hours_worked, total_overtime_hours, total_hours, active_employees, overtime_pct, hours_4w_ma, overtime_4w_ma
from main_marts.trend_timecard_hours_weekly
