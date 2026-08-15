-- source extract for wide_purchase_order_detail (PII columns excluded by the MDL projection)
select purchase_order_id, supplier_id, supplier_name, ordered_at, expected_delivery_at, total_amount, po_status, line_item_count, receipt_count, delivery_status
from main_marts.wide_purchase_order_detail
