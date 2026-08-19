-- source extract for met_monthly_product_sales (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    product_id,
    mom_revenue_growth
from main_marts.met_monthly_product_sales
