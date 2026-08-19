-- source extract for int_menu_breadth_by_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    distinct_products_sold,
    product_diversity_ratio
from main_marts.int_menu_breadth_by_store
