-- source extract for int_performance_by_department (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    department_id,
    review_quarter,
    avg_overall_score,
    employees_reviewed
from main_marts.int_performance_by_department
