-- source extract for fct_timecards (PII columns excluded by the MDL projection)
select timecard_id, employee_id, location_id, full_name, department_name, position_title, work_date, clock_in, clock_out, hours_worked, break_minutes, timecard_status, net_hours_worked, overtime_hours
from main_marts.fct_timecards
