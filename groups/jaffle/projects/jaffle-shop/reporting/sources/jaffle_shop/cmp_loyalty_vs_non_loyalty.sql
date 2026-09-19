-- source extract for cmp_loyalty_vs_non_loyalty (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_segment,
    customer_count,
    avg_lifetime_spend,
    avg_total_orders,
    repeat_rate_pct,
    revenue_share_pct
from main_marts.cmp_loyalty_vs_non_loyalty
