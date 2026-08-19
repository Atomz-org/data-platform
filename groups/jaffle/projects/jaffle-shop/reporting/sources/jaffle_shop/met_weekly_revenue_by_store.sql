-- source extract for met_weekly_revenue_by_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    week_start,
    location_id,
    wow_revenue_growth
from main_marts.met_weekly_revenue_by_store
