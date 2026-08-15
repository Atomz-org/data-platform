-- source extract for alert_overtime_excessive (PII columns excluded by the MDL projection)
select work_week, employee_id, location_id, hours_worked, overtime_hours, total_hours, overtime_pct, alert_type, severity
from main_marts.alert_overtime_excessive
