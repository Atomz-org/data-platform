-- source extract for int_shift_coverage (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id
from main_marts.int_shift_coverage
