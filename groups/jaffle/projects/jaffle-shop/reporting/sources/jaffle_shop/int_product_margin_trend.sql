-- source extract for int_product_margin_trend (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    sale_month,
    product_id,
    product_name,
    product_type,
    monthly_units_sold,
    monthly_revenue,
    gross_margin,
    gross_margin_pct,
    monthly_gross_profit,
    margin_pct_change
from main_marts.int_product_margin_trend
