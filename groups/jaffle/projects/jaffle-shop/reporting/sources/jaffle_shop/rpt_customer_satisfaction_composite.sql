-- source extract for rpt_customer_satisfaction_composite (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    satisfaction_score,
    satisfaction_tier
from main_marts.rpt_customer_satisfaction_composite
