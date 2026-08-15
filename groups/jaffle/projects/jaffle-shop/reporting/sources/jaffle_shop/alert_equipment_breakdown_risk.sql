-- source extract for alert_equipment_breakdown_risk (PII columns excluded by the MDL projection)
select equipment_id, location_id, equipment_name, equipment_type, age_days, total_maintenance_events, emergency_events, total_downtime_hours, alert_type, severity
from main_marts.alert_equipment_breakdown_risk
