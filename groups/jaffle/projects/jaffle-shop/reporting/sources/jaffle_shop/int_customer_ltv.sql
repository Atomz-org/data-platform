-- source extract for int_customer_ltv (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    lifetime_spend,
    total_orders,
    avg_order_value,
    customer_tenure_days,
    ltv_tier
from main_marts.int_customer_ltv
