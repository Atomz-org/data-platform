-- source extract for int_employee_availability (PII columns excluded by the MDL projection)
select employee_id, week_start, total_scheduled_hours, available_hours_remaining, availability_status, location_id, scheduled_shifts, morning_shifts, afternoon_shifts, evening_shifts
from main_marts.int_employee_availability
