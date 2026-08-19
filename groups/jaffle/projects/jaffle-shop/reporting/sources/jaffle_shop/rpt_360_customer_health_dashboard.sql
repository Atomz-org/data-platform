-- source extract for rpt_360_customer_health_dashboard (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    total_customers,
    high_risk_customers,
    avg_churn_score
from main_marts.rpt_360_customer_health_dashboard
