-- source extract for scr_store_health (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    store_health_score,
    health_tier
from main_marts.scr_store_health
