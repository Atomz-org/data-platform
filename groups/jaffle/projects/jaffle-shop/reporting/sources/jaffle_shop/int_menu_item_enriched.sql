-- source extract for int_menu_item_enriched (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    menu_item_id,
    product_id,
    menu_category_id,
    menu_item_name,
    menu_item_price,
    category_name,
    product_type,
    calories,
    sodium_mg,
    protein_g
from main_marts.int_menu_item_enriched
