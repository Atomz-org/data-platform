-- source extract for int_new_hire_training_progress (PII columns excluded by the MDL projection)
select employee_id, courses_completed, onboarding_status, full_name, hire_date, onboarding_end_date, courses_attempted, avg_score, first_training_date, last_completion_date
from main_marts.int_new_hire_training_progress
