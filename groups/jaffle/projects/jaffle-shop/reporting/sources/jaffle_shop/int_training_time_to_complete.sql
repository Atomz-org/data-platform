-- source extract for int_training_time_to_complete (PII columns excluded by the MDL projection)
select training_course_id, avg_days_to_complete, avg_completion_score, course_name, course_category, expected_duration_hours, total_enrollments, completed_count, min_days_to_complete, max_days_to_complete
from main_marts.int_training_time_to_complete
