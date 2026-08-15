-- source extract for stg_derived_po_line_with_product (PII columns excluded by the MDL projection)
select po_line_item_id, purchase_order_id, product_id, product_name, quantity_ordered, unit_cost, line_total
from main_marts.stg_derived_po_line_with_product
