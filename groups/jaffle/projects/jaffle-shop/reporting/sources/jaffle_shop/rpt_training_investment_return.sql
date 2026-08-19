-- source extract for rpt_training_investment_return (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    employee_id,
    training_roi_tier
from main_marts.rpt_training_investment_return
