-- source extract for int_training_progress (PII columns excluded by the MDL projection)
select employee_id, total_courses_attempted, total_courses_completed, required_courses_completed, total_required_courses, required_completion_pct, avg_completion_score, last_completion_date
from main_marts.int_training_progress
