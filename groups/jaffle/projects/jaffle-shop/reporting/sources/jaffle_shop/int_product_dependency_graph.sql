-- source extract for int_product_dependency_graph (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_a,
    product_b,
    shared_ingredient_count,
    ingredient_overlap_pct
from main_marts.int_product_dependency_graph
