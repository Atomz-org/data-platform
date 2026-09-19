-- source extract for int_purchase_orders_enriched (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    purchase_order_id,
    supplier_id,
    supplier_name,
    count_line_items,
    total_quantity_ordered,
    calculated_total_amount
from main_marts.int_purchase_orders_enriched
