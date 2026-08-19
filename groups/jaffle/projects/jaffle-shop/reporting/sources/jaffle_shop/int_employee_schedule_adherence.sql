-- source extract for int_employee_schedule_adherence (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    employee_id,
    attendance_rate_pct,
    on_time_rate_pct
from main_marts.int_employee_schedule_adherence
