-- source extract for hr_employee_journey (PII columns excluded by the MDL projection)
select employee_id, full_name, position_title, department_name, hire_date, termination_date, is_active, first_training_date, trainings_completed, first_shift_date, first_review_date, total_reviews, avg_review_score, days_hire_to_first_shift, days_hire_to_first_training
from main_marts.hr_employee_journey
