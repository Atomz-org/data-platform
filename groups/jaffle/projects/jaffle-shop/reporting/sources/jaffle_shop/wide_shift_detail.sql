-- source extract for wide_shift_detail (PII columns excluded by the MDL projection)
select shift_id, shift_date, scheduled_start, actual_end, scheduled_hours, actual_hours, employee_id, full_name, position_title, department_id, department_name, location_id, store_name, shift_cost, shift_status
from main_marts.wide_shift_detail
