-- source extract for int_po_approval_time (PII columns excluded by the MDL projection)
select purchase_order_id, days_to_approval, approval_speed, supplier_id, po_status, total_amount, created_at, ordered_at
from main_marts.int_po_approval_time
