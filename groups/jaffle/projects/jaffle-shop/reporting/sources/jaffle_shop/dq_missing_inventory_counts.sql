-- source extract for dq_missing_inventory_counts (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    location_id,
    count_status
from main_marts.dq_missing_inventory_counts
