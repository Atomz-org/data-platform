-- source extract for int_shift_coverage (PII columns excluded by the MDL projection)
select location_id, location_name, shift_date, scheduled_staff_count, total_scheduled_hours, open_time, close_time, is_closed
from main_marts.int_shift_coverage
