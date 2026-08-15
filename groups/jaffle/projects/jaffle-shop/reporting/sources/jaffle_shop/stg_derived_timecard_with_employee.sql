-- source extract for stg_derived_timecard_with_employee (PII columns excluded by the MDL projection)
select timecard_id, employee_id, full_name, department_id, location_id, work_date, hours_worked, break_minutes, timecard_status
from main_marts.stg_derived_timecard_with_employee
