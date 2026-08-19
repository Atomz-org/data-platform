-- source extract for rpt_year_in_review (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    fiscal_year,
    annual_revenue,
    revenue_yoy_growth_pct
from main_marts.rpt_year_in_review
