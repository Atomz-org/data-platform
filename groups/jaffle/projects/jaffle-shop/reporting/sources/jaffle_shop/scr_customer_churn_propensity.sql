-- source extract for scr_customer_churn_propensity (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    churn_propensity_score,
    churn_risk_tier
from main_marts.scr_customer_churn_propensity
