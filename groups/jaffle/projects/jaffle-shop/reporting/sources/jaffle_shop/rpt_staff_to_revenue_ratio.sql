-- source extract for rpt_staff_to_revenue_ratio (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    month_start,
    revenue_per_employee
from main_marts.rpt_staff_to_revenue_ratio
