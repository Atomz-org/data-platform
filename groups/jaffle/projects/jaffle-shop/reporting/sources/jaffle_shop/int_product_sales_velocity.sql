-- source extract for int_product_sales_velocity (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    sale_date,
    velocity_7d,
    velocity_28d,
    velocity_ratio,
    is_spike_day
from main_marts.int_product_sales_velocity
