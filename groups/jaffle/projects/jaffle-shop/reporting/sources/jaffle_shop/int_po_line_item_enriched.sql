-- source extract for int_po_line_item_enriched (PII columns excluded by the MDL projection)
select po_line_item_id, supplier_name, product_name, purchase_order_id, product_id, product_type, supplier_id, po_status, ordered_at, quantity_ordered, unit_cost, line_total
from main_marts.int_po_line_item_enriched
