-- source extract for met_daily_product_sales (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    sale_date,
    product_id,
    daily_margin
from main_marts.met_daily_product_sales
