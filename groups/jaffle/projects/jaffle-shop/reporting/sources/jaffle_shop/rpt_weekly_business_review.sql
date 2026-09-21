-- source extract for rpt_weekly_business_review (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    week_start,
    weekly_revenue,
    revenue_wow_pct
from main_marts.rpt_weekly_business_review
