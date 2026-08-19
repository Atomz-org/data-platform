-- source extract for int_referral_chain (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    referral_id,
    referrer_customer_id,
    referee_customer_id,
    referral_conversion_rate
from main_marts.int_referral_chain
