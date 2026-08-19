-- source extract for fct_revenue (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    revenue_date,
    net_amount,
    gross_amount,
    currency_code,
    customer_segment,
    plan_tier,
    payment_count
from main_marts.fct_revenue
