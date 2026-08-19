-- source extract for int_customer_product_preference (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    product_id,
    product_name,
    product_type,
    purchase_count,
    order_count,
    product_preference_rank,
    purchase_share_pct,
    first_purchase_date,
    last_purchase_date
from main_marts.int_customer_product_preference
