-- source extract for int_marketing_roi_by_quarter (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    roi_quarter,
    quarterly_roi_pct,
    revenue_per_marketing_dollar
from main_marts.int_marketing_roi_by_quarter
