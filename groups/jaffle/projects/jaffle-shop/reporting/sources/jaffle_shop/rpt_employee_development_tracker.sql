-- source extract for rpt_employee_development_tracker (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    employee_id,
    career_stage
from main_marts.rpt_employee_development_tracker
