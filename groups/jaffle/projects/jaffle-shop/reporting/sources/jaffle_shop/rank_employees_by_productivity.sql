-- source extract for rank_employees_by_productivity (PII columns excluded by the MDL projection)
select employee_id, avg_productivity, months_measured, productivity_rank, productivity_quartile
from main_marts.rank_employees_by_productivity
