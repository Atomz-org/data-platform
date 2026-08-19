-- source extract for int_daily_orders_by_product (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    order_date,
    product_id,
    product_name,
    product_type,
    units_sold,
    order_count,
    daily_revenue
from main_marts.int_daily_orders_by_product
