-- source extract for scr_employee_performance (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    employee_id,
    performance_score,
    performance_tier
from main_marts.scr_employee_performance
