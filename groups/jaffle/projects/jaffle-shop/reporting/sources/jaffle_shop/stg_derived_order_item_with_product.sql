-- source extract for stg_derived_order_item_with_product (PII columns excluded by the MDL projection)
select order_item_id, order_id, product_id, product_name, product_type, list_price
from main_marts.stg_derived_order_item_with_product
