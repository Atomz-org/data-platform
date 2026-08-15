-- source extract for int_employee_cross_location (PII columns excluded by the MDL projection)
select employee_id, locations_worked, location_flexibility, full_name, home_location_id, total_shifts, first_shift_date, last_shift_date
from main_marts.int_employee_cross_location
