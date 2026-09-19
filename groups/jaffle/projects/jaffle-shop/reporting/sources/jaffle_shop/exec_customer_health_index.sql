-- source extract for exec_customer_health_index (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    reporting_month,
    customer_health_index,
    active_pct,
    high_risk_pct
from main_marts.exec_customer_health_index
