-- source extract for dq_stale_pricing (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    days_since_last_change,
    staleness_level
from main_marts.dq_stale_pricing
