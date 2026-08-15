-- source extract for dim_equipment (PII columns excluded by the MDL projection)
select equipment_id, location_id, location_name, equipment_name, equipment_type, manufacturer, model_number, serial_number, equipment_status, purchase_cost, purchase_date, warranty_expiry_date, last_maintenance_date, is_under_warranty, equipment_age_days
from main_marts.dim_equipment
