-- source extract for int_weekly_product_sales (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    week_start,
    product_id,
    product_name,
    units_sold,
    weekly_revenue,
    avg_daily_units
from main_marts.int_weekly_product_sales
