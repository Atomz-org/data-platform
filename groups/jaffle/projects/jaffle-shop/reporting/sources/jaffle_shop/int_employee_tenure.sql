-- source extract for int_employee_tenure (PII columns excluded by the MDL projection)
select employee_id, hire_date, termination_date, employment_status, tenure_days, tenure_months, tenure_bucket
from main_marts.int_employee_tenure
