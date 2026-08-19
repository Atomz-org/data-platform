-- source extract for int_revenue_per_employee_hour (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    store_id,
    work_date,
    revenue_per_labor_hour,
    revenue_per_employee
from main_marts.int_revenue_per_employee_hour
