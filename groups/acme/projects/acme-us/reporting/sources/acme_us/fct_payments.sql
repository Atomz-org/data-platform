-- source extract for fct_payments (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    payment_id,
    amount,
    paid_at,
    currency_code,
    payment_status,
    customer_segment,
    country_code,
    plan_tier,
    customer_id,
    subscription_id
from main_marts.fct_payments
