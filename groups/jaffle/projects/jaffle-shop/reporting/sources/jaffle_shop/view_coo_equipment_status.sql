-- source extract for view_coo_equipment_status (PII columns excluded by the MDL projection)
select equipment_id, location_id, equipment_name, equipment_type, total_downtime_hours, total_maintenance_events, avg_downtime_per_event, emergency_pct, equipment_condition, requires_attention
from main_marts.view_coo_equipment_status
