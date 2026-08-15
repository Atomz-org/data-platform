-- source extract for kpi_equipment_uptime (PII columns excluded by the MDL projection)
select equipment_id, location_id, age_days, total_downtime_hours, uptime_days, uptime_pct
from main_marts.kpi_equipment_uptime
