-- source extract for int_shift_actual_vs_scheduled (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    shift_id,
    hours_variance,
    schedule_adherence_status
from main_marts.int_shift_actual_vs_scheduled
