-- source extract for rpt_360_workforce_dashboard (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    active_employees,
    turnover_rate_pct
from main_marts.rpt_360_workforce_dashboard
