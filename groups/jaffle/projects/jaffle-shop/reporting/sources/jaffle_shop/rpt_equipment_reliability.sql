-- source extract for rpt_equipment_reliability (PII columns excluded by the MDL projection)
select equipment_id, equipment_name, equipment_type, location_id, location_name, equipment_age_days, is_under_warranty, total_maintenance_events, total_downtime_hours, total_maintenance_cost, total_emergency_events, total_preventive_events, avg_monthly_downtime_hours, avg_downtime_per_event, emergency_pct
from main_marts.rpt_equipment_reliability
