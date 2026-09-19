-- source extract for cmp_new_vs_returning_customers (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    order_month,
    new_customers,
    returning_customers,
    returning_revenue_share_pct,
    returning_customer_share_pct
from main_marts.cmp_new_vs_returning_customers
