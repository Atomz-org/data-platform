-- source extract for hr_cross_training_coverage (PII columns excluded by the MDL projection)
select employee_id, full_name, home_department, position_title, departments_trained_in, total_courses_completed, cross_dept_courses, versatility_level
from main_marts.hr_cross_training_coverage
