-- source extract for int_purchase_orders_enriched (PII columns excluded by the MDL projection)
select purchase_order_id, supplier_id, supplier_name, count_line_items, total_quantity_ordered, calculated_total_amount, warehouse_id, po_status, total_amount, ordered_at, expected_delivery_at, created_at
from main_marts.int_purchase_orders_enriched
