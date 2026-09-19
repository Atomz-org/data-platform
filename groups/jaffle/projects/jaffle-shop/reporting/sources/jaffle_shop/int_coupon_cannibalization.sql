-- source extract for int_coupon_cannibalization (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    coupon_id,
    cannibalization_rate,
    incremental_redemptions,
    cannibalized_redemptions
from main_marts.int_coupon_cannibalization
