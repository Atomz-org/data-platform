-- source extract for int_absenteeism_rate (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    employee_id
from main_marts.int_absenteeism_rate
