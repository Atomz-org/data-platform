-- source extract for alert_employee_no_show_pattern (PII columns excluded by the MDL projection)
select employee_id, shift_date, location_id, no_shows_30d, alert_type, severity
from main_marts.alert_employee_no_show_pattern
