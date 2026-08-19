-- source extract for int_coupon_time_to_redemption (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    coupon_id,
    days_to_first_redemption,
    redemption_speed
from main_marts.int_coupon_time_to_redemption
