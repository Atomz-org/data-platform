-- source extract for int_equipment_cost_per_store (PII columns excluded by the MDL projection)
select location_id, total_equipment_cost, avg_total_cost_per_equipment, equipment_count, total_purchase_cost, total_maintenance_cost, avg_purchase_cost, total_maintenance_events, total_downtime_hours
from main_marts.int_equipment_cost_per_store
