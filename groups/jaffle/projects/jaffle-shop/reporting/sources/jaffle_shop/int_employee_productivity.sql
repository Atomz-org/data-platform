-- source extract for int_employee_productivity (PII columns excluded by the MDL projection)
select employee_id, location_id, work_date, total_hours_worked, orders_handled, orders_per_hour, hours_per_order
from main_marts.int_employee_productivity
