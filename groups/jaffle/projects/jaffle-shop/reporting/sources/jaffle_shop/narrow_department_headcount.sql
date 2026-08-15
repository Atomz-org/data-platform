-- source extract for narrow_department_headcount (PII columns excluded by the MDL projection)
select department_name, headcount
from main_marts.narrow_department_headcount
