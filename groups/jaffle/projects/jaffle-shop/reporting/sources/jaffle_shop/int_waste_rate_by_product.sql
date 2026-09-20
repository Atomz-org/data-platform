-- source extract for int_waste_rate_by_product (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    total_waste_events,
    total_quantity_wasted,
    total_cost_of_waste,
    waste_rate
from main_marts.int_waste_rate_by_product
