-- source extract for stg_derived_employee_with_position (PII columns excluded by the MDL projection)
select employee_id, full_name, position_id, position_title, pay_grade, department_id, location_id, hire_date, employment_status
from main_marts.stg_derived_employee_with_position
