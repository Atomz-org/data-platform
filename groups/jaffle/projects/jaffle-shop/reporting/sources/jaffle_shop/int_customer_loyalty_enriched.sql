-- source extract for int_customer_loyalty_enriched (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    current_tier,
    loyalty_points_balance,
    loyalty_lifecycle_stage
from main_marts.int_customer_loyalty_enriched
