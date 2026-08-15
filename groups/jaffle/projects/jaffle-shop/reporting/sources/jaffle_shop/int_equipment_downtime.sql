-- source extract for int_equipment_downtime (PII columns excluded by the MDL projection)
select equipment_id, equipment_name, equipment_type, location_id, downtime_month, maintenance_event_count, total_downtime_hours, total_maintenance_cost, emergency_count, preventive_count
from main_marts.int_equipment_downtime
