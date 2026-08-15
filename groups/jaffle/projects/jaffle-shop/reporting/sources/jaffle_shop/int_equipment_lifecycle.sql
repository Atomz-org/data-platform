-- source extract for int_equipment_lifecycle (PII columns excluded by the MDL projection)
select equipment_id, location_id, equipment_name, equipment_type, equipment_status, purchase_date, purchase_cost, warranty_expiry_date, age_days, age_months, is_under_warranty, total_maintenance_events, total_maintenance_cost, total_downtime_hours, emergency_events, preventive_events, annualized_maintenance_frequency, maintenance_cost_pct_of_purchase, lifecycle_status
from main_marts.int_equipment_lifecycle
