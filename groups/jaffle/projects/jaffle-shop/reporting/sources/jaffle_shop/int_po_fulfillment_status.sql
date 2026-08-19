-- source extract for int_po_fulfillment_status (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    purchase_order_id,
    supplier_id,
    po_fulfillment_status,
    total_quantity_ordered,
    total_quantity_received
from main_marts.int_po_fulfillment_status
