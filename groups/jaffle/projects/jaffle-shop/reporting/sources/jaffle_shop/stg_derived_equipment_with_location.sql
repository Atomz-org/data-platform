-- source extract for stg_derived_equipment_with_location (PII columns excluded by the MDL projection)
select equipment_id, equipment_name, equipment_type, location_id, location_name, purchase_date, equipment_status
from main_marts.stg_derived_equipment_with_location
