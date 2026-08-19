-- source extract for int_ingredient_usage_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    order_date,
    ingredient_id,
    quantity_unit,
    total_quantity_used,
    order_item_count
from main_marts.int_ingredient_usage_daily
