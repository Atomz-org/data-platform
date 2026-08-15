-- source extract for int_absenteeism_rate (PII columns excluded by the MDL projection)
select employee_id, location_id, total_scheduled_shifts, absent_shifts, attended_shifts, absenteeism_rate_pct, first_shift_date, last_shift_date
from main_marts.int_absenteeism_rate
