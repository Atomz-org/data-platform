-- source extract for met_monthly_revenue_by_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    location_id,
    mom_revenue_growth,
    yoy_revenue_growth,
    fiscal_year,
    fiscal_quarter
from main_marts.met_monthly_revenue_by_store
