-- source extract for scr_menu_item_ranking (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    composite_score,
    overall_composite_rank,
    category_composite_rank
from main_marts.scr_menu_item_ranking
