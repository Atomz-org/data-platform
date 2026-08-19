-- source extract for int_menu_item_margin (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    menu_item_id,
    menu_item_name,
    menu_item_price,
    total_ingredient_cost,
    gross_margin,
    gross_margin_pct
from main_marts.int_menu_item_margin
