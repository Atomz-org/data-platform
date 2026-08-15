-- source extract for fct_purchase_orders (PII columns excluded by the MDL projection)
select purchase_order_id, supplier_id, supplier_name, warehouse_id, po_status, total_amount, count_line_items, total_quantity_ordered, calculated_total_amount, ordered_at, expected_delivery_at, created_at, is_cancelled, is_completed
from main_marts.fct_purchase_orders
