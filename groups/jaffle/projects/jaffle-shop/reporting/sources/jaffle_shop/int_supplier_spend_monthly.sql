-- source extract for int_supplier_spend_monthly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    supplier_id,
    supplier_name,
    order_month,
    count_purchase_orders,
    total_spend,
    avg_unit_cost
from main_marts.int_supplier_spend_monthly
