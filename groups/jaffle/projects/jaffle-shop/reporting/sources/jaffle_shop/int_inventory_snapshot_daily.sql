-- source extract for int_inventory_snapshot_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    location_id,
    counted_on_hand,
    system_quantity,
    count_variance
from main_marts.int_inventory_snapshot_daily
