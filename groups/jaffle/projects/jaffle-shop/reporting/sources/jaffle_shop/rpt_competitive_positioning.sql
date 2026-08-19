-- source extract for rpt_competitive_positioning (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    competitive_position
from main_marts.rpt_competitive_positioning
