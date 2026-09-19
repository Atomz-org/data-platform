-- source extract for int_seasonal_sales_pattern (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    product_name,
    season_name,
    promotion_name,
    is_during_promotion,
    total_units_sold,
    total_revenue,
    avg_daily_units
from main_marts.int_seasonal_sales_pattern
