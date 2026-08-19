-- source extract for int_price_elasticity_estimate (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    price_changed_date,
    estimated_elasticity
from main_marts.int_price_elasticity_estimate
