-- source extract for stg_derived_maintenance_with_equipment (PII columns excluded by the MDL projection)
select maintenance_log_id, equipment_id, equipment_name, equipment_type, location_id, scheduled_date, maintenance_type, maintenance_cost, maintenance_description
from main_marts.stg_derived_maintenance_with_equipment
