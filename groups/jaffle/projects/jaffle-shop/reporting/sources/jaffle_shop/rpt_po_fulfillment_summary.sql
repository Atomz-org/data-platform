-- source extract for rpt_po_fulfillment_summary (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, purchase_order_id, po_status, po_fulfillment_status, ordered_at, expected_delivery_at, total_line_items, total_quantity_ordered, total_quantity_received, count_lines_fully_received, quantity_fill_rate, line_fill_rate
from main_marts.rpt_po_fulfillment_summary
