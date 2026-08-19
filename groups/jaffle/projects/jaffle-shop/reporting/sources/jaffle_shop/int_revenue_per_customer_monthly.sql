-- source extract for int_revenue_per_customer_monthly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    revenue_month,
    total_revenue
from main_marts.int_revenue_per_customer_monthly
