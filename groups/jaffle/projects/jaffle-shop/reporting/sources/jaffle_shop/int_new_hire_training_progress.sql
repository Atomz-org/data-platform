-- source extract for int_new_hire_training_progress (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    employee_id,
    courses_completed,
    onboarding_status
from main_marts.int_new_hire_training_progress
