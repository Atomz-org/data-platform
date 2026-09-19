-- source extract for int_revenue_by_product_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    revenue_date,
    product_id,
    product_name,
    product_type,
    units_sold,
    product_revenue,
    avg_unit_price,
    revenue_per_unit
from main_marts.int_revenue_by_product_daily
