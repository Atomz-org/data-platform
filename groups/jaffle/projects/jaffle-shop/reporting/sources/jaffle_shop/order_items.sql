-- source extract for order_items (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    order_item_id,
    order_id,
    product_id,
    ordered_at,
    product_name,
    product_price,
    is_food_item,
    is_drink_item,
    supply_cost
from main_marts.order_items
