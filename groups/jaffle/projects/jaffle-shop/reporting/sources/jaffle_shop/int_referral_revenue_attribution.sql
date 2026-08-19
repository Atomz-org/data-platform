-- source extract for int_referral_revenue_attribution (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    referrer_customer_id,
    total_attributed_revenue,
    net_referral_revenue
from main_marts.int_referral_revenue_attribution
