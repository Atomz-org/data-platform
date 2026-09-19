-- source extract for int_gross_margin_by_product (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    gross_margin,
    gross_margin_pct
from main_marts.int_gross_margin_by_product
