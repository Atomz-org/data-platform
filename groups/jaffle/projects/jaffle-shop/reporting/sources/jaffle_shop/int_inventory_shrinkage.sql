-- source extract for int_inventory_shrinkage (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    location_id,
    shrinkage_quantity,
    shrinkage_pct,
    shrinkage_status
from main_marts.int_inventory_shrinkage
