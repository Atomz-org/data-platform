-- source extract for customers (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    customer_name,
    count_lifetime_orders,
    first_ordered_at,
    last_ordered_at,
    lifetime_spend_pretax,
    lifetime_tax_paid,
    lifetime_spend,
    customer_type
from main_marts.customers
