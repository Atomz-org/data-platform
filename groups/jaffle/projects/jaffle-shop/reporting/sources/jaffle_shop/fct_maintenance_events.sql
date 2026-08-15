-- source extract for fct_maintenance_events (PII columns excluded by the MDL projection)
select maintenance_log_id, equipment_id, equipment_name, equipment_type, location_id, location_name, technician_id, maintenance_type, maintenance_description, maintenance_status, maintenance_cost, downtime_hours, scheduled_date, completed_date, is_under_warranty, is_emergency
from main_marts.fct_maintenance_events
