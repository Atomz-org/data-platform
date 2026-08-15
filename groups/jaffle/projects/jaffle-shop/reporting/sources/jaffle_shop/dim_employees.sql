-- source extract for dim_employees (PII columns excluded by the MDL projection)
select employee_id, first_name, last_name, full_name, email, employment_status, hire_date, termination_date, location_id, department_id, department_name, position_id, position_title, pay_grade, min_hourly_rate, max_hourly_rate, is_management, tenure_days, tenure_months, tenure_bucket, is_active
from main_marts.dim_employees
