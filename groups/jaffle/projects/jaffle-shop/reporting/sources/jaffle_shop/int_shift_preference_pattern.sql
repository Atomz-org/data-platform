-- source extract for int_shift_preference_pattern (PII columns excluded by the MDL projection)
select location_id, shift_type, day_of_week, day_name, shift_count, unique_employees, no_show_count, completed_count, no_show_rate_pct, popularity_rank, worst_attendance_rank
from main_marts.int_shift_preference_pattern
