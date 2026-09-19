-- source extract for int_referral_conversion_rate (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    total_referrals,
    status_conversion_rate,
    purchase_conversion_rate,
    referral_program_roi
from main_marts.int_referral_conversion_rate
