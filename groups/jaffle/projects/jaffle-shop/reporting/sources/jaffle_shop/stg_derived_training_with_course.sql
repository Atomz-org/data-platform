-- source extract for stg_derived_training_with_course (PII columns excluded by the MDL projection)
select training_completion_id, employee_id, training_course_id, course_name, course_category, expected_duration, started_date, completed_date, completion_score
from main_marts.stg_derived_training_with_course
