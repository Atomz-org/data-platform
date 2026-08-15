-- source extract for alert_training_overdue (PII columns excluded by the MDL projection)
select employee_id, full_name, location_id, last_training_date, days_since_training, alert_type, severity
from main_marts.alert_training_overdue
