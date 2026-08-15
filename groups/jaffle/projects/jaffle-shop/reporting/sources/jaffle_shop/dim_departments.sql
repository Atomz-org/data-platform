-- source extract for dim_departments (PII columns excluded by the MDL projection)
select department_id, department_name, department_description
from main_marts.dim_departments
