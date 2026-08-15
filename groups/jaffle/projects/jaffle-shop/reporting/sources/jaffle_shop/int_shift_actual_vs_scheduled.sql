-- source extract for int_shift_actual_vs_scheduled (PII columns excluded by the MDL projection)
select shift_id, hours_variance, schedule_adherence_status, employee_id, location_id, shift_date, shift_type, scheduled_start, scheduled_end, scheduled_hours, clock_in, clock_out, actual_hours
from main_marts.int_shift_actual_vs_scheduled
