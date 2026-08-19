-- source extract for int_invoice_line_items_enriched (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    invoice_line_item_id,
    invoice_id,
    product_id,
    product_name,
    product_type,
    quantity,
    unit_price,
    line_total,
    list_price,
    price_variance
from main_marts.int_invoice_line_items_enriched
