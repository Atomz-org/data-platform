-- source extract for int_shift_pattern_by_employee (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    employee_id,
    primary_shift_pattern,
    shift_variety
from main_marts.int_shift_pattern_by_employee
