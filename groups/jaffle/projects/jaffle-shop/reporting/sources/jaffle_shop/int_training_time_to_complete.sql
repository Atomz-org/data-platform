-- source extract for int_training_time_to_complete (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    training_course_id,
    avg_days_to_complete,
    avg_completion_score
from main_marts.int_training_time_to_complete
