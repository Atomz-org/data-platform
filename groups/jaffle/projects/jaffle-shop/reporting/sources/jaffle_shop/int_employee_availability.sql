-- source extract for int_employee_availability (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    employee_id,
    week_start,
    total_scheduled_hours,
    available_hours_remaining,
    availability_status
from main_marts.int_employee_availability
