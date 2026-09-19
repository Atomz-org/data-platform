-- source extract for int_customer_status_monthly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    customer_id,
    customer_status,
    days_since_last_order,
    lifetime_orders
from main_marts.int_customer_status_monthly
