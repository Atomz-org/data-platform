-- source extract for rpt_360_store_health_dashboard (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    health_score,
    health_tier
from main_marts.rpt_360_store_health_dashboard
