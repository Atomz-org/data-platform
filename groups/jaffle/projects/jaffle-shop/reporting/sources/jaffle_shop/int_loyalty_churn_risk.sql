-- source extract for int_loyalty_churn_risk (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    loyalty_member_id,
    days_since_last_transaction,
    churn_risk_level,
    is_declining_activity
from main_marts.int_loyalty_churn_risk
