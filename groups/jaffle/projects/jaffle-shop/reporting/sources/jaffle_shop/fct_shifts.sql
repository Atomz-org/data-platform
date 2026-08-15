-- source extract for fct_shifts (PII columns excluded by the MDL projection)
select shift_id, employee_id, location_id, full_name, department_name, position_title, location_name, shift_date, shift_type, shift_status, scheduled_start, scheduled_end, actual_start, actual_end, scheduled_hours, actual_hours, is_no_show, is_late_arrival
from main_marts.fct_shifts
