-- source extract for int_maintenance_frequency (PII columns excluded by the MDL projection)
select equipment_type, location_id, total_maintenance_events, avg_events_per_equipment, preventive_count, corrective_count, emergency_count, total_maintenance_cost, avg_maintenance_cost, total_downtime_hours, avg_downtime_hours, equipment_count
from main_marts.int_maintenance_frequency
