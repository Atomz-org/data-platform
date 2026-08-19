-- source extract for met_daily_customer_metrics (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    activity_date,
    active_customers,
    new_customers,
    returning_customers
from main_marts.met_daily_customer_metrics
