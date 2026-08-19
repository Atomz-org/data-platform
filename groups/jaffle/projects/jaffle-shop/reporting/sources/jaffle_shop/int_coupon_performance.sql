-- source extract for int_coupon_performance (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    coupon_id,
    total_redemptions,
    redemption_rate,
    total_discount_given
from main_marts.int_coupon_performance
