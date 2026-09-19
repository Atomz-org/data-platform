-- source extract for int_new_vs_returning_product_mix (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    customer_type,
    item_count,
    total_revenue
from main_marts.int_new_vs_returning_product_mix
