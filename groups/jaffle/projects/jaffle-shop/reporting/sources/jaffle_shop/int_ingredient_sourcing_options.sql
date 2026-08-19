-- source extract for int_ingredient_sourcing_options (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    supplier_id,
    cost_rank,
    available_supplier_count
from main_marts.int_ingredient_sourcing_options
