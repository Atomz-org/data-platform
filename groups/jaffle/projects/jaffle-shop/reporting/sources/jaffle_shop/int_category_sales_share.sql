-- source extract for int_category_sales_share (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    category,
    location_id,
    revenue_share_pct
from main_marts.int_category_sales_share
