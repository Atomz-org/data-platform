-- source extract for int_shift_pattern_by_employee (PII columns excluded by the MDL projection)
select employee_id, primary_shift_pattern, shift_variety, location_id, total_shifts, morning_count, afternoon_count, evening_count, total_scheduled_hours, avg_shift_hours
from main_marts.int_shift_pattern_by_employee
