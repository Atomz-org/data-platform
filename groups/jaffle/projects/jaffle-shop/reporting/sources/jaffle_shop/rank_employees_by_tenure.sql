-- source extract for rank_employees_by_tenure (PII columns excluded by the MDL projection)
select employee_id, full_name, tenure_days, department_id, is_active, tenure_rank, dept_tenure_rank, tenure_quartile
from main_marts.rank_employees_by_tenure
