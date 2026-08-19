-- source extract for int_po_approval_time (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    purchase_order_id,
    days_to_approval,
    approval_speed
from main_marts.int_po_approval_time
