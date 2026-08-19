-- source extract for orders (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    order_id,
    customer_id,
    order_total,
    ordered_at,
    order_cost,
    is_food_order,
    is_drink_order,
    location_id,
    subtotal_cents,
    tax_paid_cents,
    order_total_cents,
    subtotal,
    tax_paid,
    order_items_subtotal,
    count_food_items,
    count_drink_items,
    count_order_items,
    customer_order_number
from main_marts.orders
