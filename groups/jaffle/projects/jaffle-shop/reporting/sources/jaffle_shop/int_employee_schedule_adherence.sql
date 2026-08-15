-- source extract for int_employee_schedule_adherence (PII columns excluded by the MDL projection)
select employee_id, attendance_rate_pct, on_time_rate_pct, location_id, total_scheduled_shifts, shifts_worked, shifts_on_time, shifts_missed
from main_marts.int_employee_schedule_adherence
