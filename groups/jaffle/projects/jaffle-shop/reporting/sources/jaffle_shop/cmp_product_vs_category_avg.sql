-- source extract for cmp_product_vs_category_avg (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    product_name,
    category_name,
    revenue_vs_category,
    revenue_index,
    margin_vs_category_pp
from main_marts.cmp_product_vs_category_avg
