-- source extract for wide_maintenance_detail (PII columns excluded by the MDL projection)
select maintenance_log_id, equipment_id, equipment_name, equipment_type, location_id, store_name, scheduled_date, maintenance_type, maintenance_cost, downtime_hours, maintenance_description, maintenance_category, cost_per_downtime_hour
from main_marts.wide_maintenance_detail
