-- source extract for int_avg_basket_composition (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    avg_items_per_order,
    avg_basket_value,
    single_item_orders,
    large_basket_orders
from main_marts.int_avg_basket_composition
