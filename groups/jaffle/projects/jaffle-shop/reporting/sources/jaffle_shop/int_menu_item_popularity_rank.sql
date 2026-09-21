-- source extract for int_menu_item_popularity_rank (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    product_name,
    product_type,
    menu_category_id,
    category_name,
    total_units_sold,
    total_revenue,
    volume_rank_in_category,
    revenue_rank_in_category,
    overall_volume_rank,
    overall_revenue_rank
from main_marts.int_menu_item_popularity_rank
