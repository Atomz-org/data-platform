-- source extract for int_monthly_active_customers (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    total_customer_visits,
    new_customers,
    returning_customer_visits,
    mom_customer_visit_change,
    mom_new_customer_change
from main_marts.int_monthly_active_customers
