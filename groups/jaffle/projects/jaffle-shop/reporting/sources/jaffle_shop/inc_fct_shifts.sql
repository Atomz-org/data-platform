-- source extract for inc_fct_shifts (PII columns excluded by the MDL projection)
select shift_id, employee_id, location_id, shift_date, scheduled_start, scheduled_end, scheduled_hours, shift_month
from main_marts.inc_fct_shifts
