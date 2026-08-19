-- source extract for cmp_yoy_revenue_by_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    current_month,
    current_revenue,
    prior_year_revenue,
    yoy_revenue_growth_pct
from main_marts.cmp_yoy_revenue_by_store
