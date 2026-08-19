-- source extract for int_overtime_by_department (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    department_id,
    overtime_month,
    total_overtime_hours,
    employees_with_overtime
from main_marts.int_overtime_by_department
