-- source extract for int_ingredient_usage_variance (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    usage_date,
    usage_variance,
    variance_pct
from main_marts.int_ingredient_usage_variance
