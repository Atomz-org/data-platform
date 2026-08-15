-- source extract for int_employee_enriched (PII columns excluded by the MDL projection)
select employee_id, location_id, first_name, last_name, full_name, email, employment_status, hire_date, termination_date, department_id, department_name, position_id, position_title, pay_grade, min_hourly_rate, max_hourly_rate, is_management
from main_marts.int_employee_enriched
