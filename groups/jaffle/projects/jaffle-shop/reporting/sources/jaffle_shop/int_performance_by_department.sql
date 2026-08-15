-- source extract for int_performance_by_department (PII columns excluded by the MDL projection)
select department_id, review_quarter, avg_overall_score, employees_reviewed, department_name, review_count, avg_attendance_score, avg_quality_score, avg_teamwork_score, min_overall_score, max_overall_score
from main_marts.int_performance_by_department
