-- source extract for rpt_quarterly_strategic_review (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    quarter_start,
    quarterly_revenue,
    revenue_yoy_pct
from main_marts.rpt_quarterly_strategic_review
