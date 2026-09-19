-- source extract for int_equipment_cost_per_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    total_equipment_cost,
    avg_total_cost_per_equipment
from main_marts.int_equipment_cost_per_store
