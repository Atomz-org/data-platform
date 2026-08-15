-- source extract for stg_derived_employee_with_department (PII columns excluded by the MDL projection)
select employee_id, full_name, department_id, department_name, location_id, hire_date, employment_status
from main_marts.stg_derived_employee_with_department
