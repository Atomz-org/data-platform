-- source extract for dq_shift_overlap_check (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    shift_id_1,
    shift_id_2,
    employee_id
from main_marts.dq_shift_overlap_check
