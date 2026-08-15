-- source extract for hr_onboarding_time_to_value (PII columns excluded by the MDL projection)
select employee_id, full_name, department_name, hire_date, months_to_dept_avg, ramp_category
from main_marts.hr_onboarding_time_to_value
