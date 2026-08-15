-- source extract for stg_derived_shift_with_employee (PII columns excluded by the MDL projection)
select shift_id, employee_id, full_name, department_id, location_id, shift_date, scheduled_start, scheduled_end, scheduled_hours, shift_status
from main_marts.stg_derived_shift_with_employee
