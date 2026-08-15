-- source extract for alert_maintenance_overdue (PII columns excluded by the MDL projection)
select equipment_id, location_id, equipment_name, age_days, total_maintenance_events, preventive_events, alert_type, severity
from main_marts.alert_maintenance_overdue
