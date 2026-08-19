-- source extract for int_po_line_item_enriched (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    po_line_item_id,
    supplier_name,
    product_name
from main_marts.int_po_line_item_enriched
