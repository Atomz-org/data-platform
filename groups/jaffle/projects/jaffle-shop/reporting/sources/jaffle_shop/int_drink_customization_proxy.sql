-- source extract for int_drink_customization_proxy (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    menu_category_id,
    product_count,
    menu_item_count,
    variety_level
from main_marts.int_drink_customization_proxy
