-- source extract for int_inventory_movement_enriched (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    movement_id,
    product_name,
    location_name,
    inbound_quantity,
    outbound_quantity
from main_marts.int_inventory_movement_enriched
