-- source extract for rpt_equipment_replacement_plan (PII columns excluded by the MDL projection)
select equipment_id, location_id, location_name, equipment_name, equipment_type, equipment_status, purchase_date, purchase_cost, warranty_expiry_date, is_under_warranty, age_months, total_maintenance_events, total_maintenance_cost, total_downtime_hours, emergency_events, annualized_maintenance_frequency, maintenance_cost_pct_of_purchase, lifecycle_status, replacement_priority, replacement_reason, total_cost_of_ownership, monthly_cost_of_ownership
from main_marts.rpt_equipment_replacement_plan
