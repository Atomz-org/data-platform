-- source extract for int_reorder_point_calc (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    location_id,
    reorder_point,
    suggested_reorder_quantity,
    needs_reorder
from main_marts.int_reorder_point_calc
