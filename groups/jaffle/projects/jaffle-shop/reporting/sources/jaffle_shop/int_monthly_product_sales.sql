-- source extract for int_monthly_product_sales (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    product_id,
    product_name,
    units_sold,
    monthly_revenue,
    mom_revenue_growth
from main_marts.int_monthly_product_sales
