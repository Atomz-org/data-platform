-- source extract for int_revenue_concentration_index (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    herfindahl_index,
    concentration_level
from main_marts.int_revenue_concentration_index
