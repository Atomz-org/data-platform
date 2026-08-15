-- source extract for int_labor_hours_actual (PII columns excluded by the MDL projection)
select employee_id, location_id, work_date, total_hours_worked, total_break_minutes, timecard_entries
from main_marts.int_labor_hours_actual
