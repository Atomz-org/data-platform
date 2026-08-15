-- source extract for int_invoice_line_items_enriched (PII columns excluded by the MDL projection)
select invoice_line_item_id, invoice_id, product_id, product_name, product_type, quantity, unit_price, line_total, list_price, price_variance, is_food_item, is_drink_item, line_item_description
from main_marts.int_invoice_line_items_enriched
