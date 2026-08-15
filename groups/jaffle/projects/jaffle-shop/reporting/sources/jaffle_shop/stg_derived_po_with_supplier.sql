-- source extract for stg_derived_po_with_supplier (PII columns excluded by the MDL projection)
select purchase_order_id, supplier_id, supplier_name, ordered_at, expected_delivery_at, total_amount, po_status
from main_marts.stg_derived_po_with_supplier
