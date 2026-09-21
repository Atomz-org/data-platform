-- source extract for int_coupon_usage_by_customer_segment (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_segment,
    total_redemptions,
    unique_customers,
    redemptions_per_customer
from main_marts.int_coupon_usage_by_customer_segment
