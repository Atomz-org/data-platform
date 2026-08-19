-- source extract for int_coupon_geographic_performance (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    discount_type,
    total_redemptions
from main_marts.int_coupon_geographic_performance
