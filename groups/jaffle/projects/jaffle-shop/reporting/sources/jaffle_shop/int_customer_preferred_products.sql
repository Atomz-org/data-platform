-- source extract for int_customer_preferred_products (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    top1_product_name,
    top1_purchase_count
from main_marts.int_customer_preferred_products
