-- source extract for int_seasonal_product_index (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    sales_month,
    seasonality_index,
    season_type
from main_marts.int_seasonal_product_index
