-- source extract for int_maintenance_frequency (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    equipment_type,
    location_id,
    total_maintenance_events,
    avg_events_per_equipment
from main_marts.int_maintenance_frequency
