-- source extract for int_employee_roster_monthly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    location_id,
    headcount,
    management_count,
    new_hires_in_month,
    terminations_in_month
from main_marts.int_employee_roster_monthly
