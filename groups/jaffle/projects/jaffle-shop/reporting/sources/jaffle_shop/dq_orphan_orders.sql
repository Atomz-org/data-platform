-- source extract for dq_orphan_orders (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    order_id,
    customer_id,
    order_total
from main_marts.dq_orphan_orders
