-- source extract for int_customer_first_purchase_context (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    first_order_id,
    first_order_date,
    first_store_name,
    first_order_total,
    first_order_distinct_products,
    first_order_day_name,
    first_order_is_weekend
from main_marts.int_customer_first_purchase_context
