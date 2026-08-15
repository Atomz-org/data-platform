-- source extract for hr_training_gap_analysis (PII columns excluded by the MDL projection)
select employee_id, full_name, position_title, department_name, required_courses, completed_courses, missing_courses, training_completion_pct
from main_marts.hr_training_gap_analysis
