-- source extract for int_revenue_by_customer_segment (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    rfm_segment,
    revenue_month,
    segment_revenue,
    customer_count
from main_marts.int_revenue_by_customer_segment
