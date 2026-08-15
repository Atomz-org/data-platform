-- source extract for alert_understaffed_shift (PII columns excluded by the MDL projection)
select shift_date, location_id, scheduled_shifts, completed_shifts, no_show_shifts, no_show_pct, alert_type, severity
from main_marts.alert_understaffed_shift
