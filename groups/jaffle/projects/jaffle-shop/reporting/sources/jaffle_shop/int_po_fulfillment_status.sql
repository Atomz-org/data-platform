-- source extract for int_po_fulfillment_status (PII columns excluded by the MDL projection)
select purchase_order_id, supplier_id, po_fulfillment_status, total_quantity_ordered, total_quantity_received, po_status, ordered_at, expected_delivery_at, total_line_items, count_lines_fully_received
from main_marts.int_po_fulfillment_status
