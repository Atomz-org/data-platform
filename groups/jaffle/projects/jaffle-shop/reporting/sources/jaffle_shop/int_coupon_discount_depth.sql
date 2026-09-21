-- source extract for int_coupon_discount_depth (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    discount_type,
    avg_effective_discount_pct
from main_marts.int_coupon_discount_depth
