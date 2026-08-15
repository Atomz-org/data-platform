-- source extract for inc_fct_timecards (PII columns excluded by the MDL projection)
select timecard_id, employee_id, location_id, clock_in, clock_out, hours_worked, break_minutes, work_date, work_month
from main_marts.inc_fct_timecards
