-- source extract for cmp_seasonal_yoy (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    current_fiscal_year,
    fiscal_quarter,
    current_revenue,
    prior_year_revenue,
    yoy_revenue_growth_pct
from main_marts.cmp_seasonal_yoy
