-- source extract for rank_employees_by_performance (PII columns excluded by the MDL projection)
select employee_id, avg_overall_score, review_count, performance_rank, performance_quartile, performance_band
from main_marts.rank_employees_by_performance
