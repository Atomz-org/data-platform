-- source extract for int_product_return_rate (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    waste_rate_pct,
    waste_cost_as_pct_of_revenue
from main_marts.int_product_return_rate
