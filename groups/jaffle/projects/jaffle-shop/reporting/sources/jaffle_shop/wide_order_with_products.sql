-- source extract for wide_order_with_products (PII columns excluded by the MDL projection)
select order_id, order_item_id, product_id, menu_item_name, menu_category_id, menu_price, quantity, supply_cost, line_revenue, discount_amount, gross_margin_pct, line_margin
from main_marts.wide_order_with_products
