-- source extract for dim_training_courses (PII columns excluded by the MDL projection)
select training_course_id, course_name, course_description, course_category, duration_hours, is_required, is_active
from main_marts.dim_training_courses
