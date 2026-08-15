-- source extract for inc_fct_order_items (PII columns excluded by the MDL projection)
select order_item_id, order_id, ordered_at, product_id, product_name, quantity, supply_cost, gross_item_revenue, item_margin
from main_marts.inc_fct_order_items
