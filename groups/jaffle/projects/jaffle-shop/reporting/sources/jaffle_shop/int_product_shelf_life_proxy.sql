-- source extract for int_product_shelf_life_proxy (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    avg_days_between_sales,
    freshness_tier
from main_marts.int_product_shelf_life_proxy
