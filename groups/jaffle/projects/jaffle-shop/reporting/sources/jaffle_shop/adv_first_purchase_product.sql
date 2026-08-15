-- source extract for adv_first_purchase_product (PII columns excluded by the MDL projection)
select customer_id, customer_name, first_order_id, first_order_date, first_order_total, product_id, product_name, product_type, product_price
from main_marts.adv_first_purchase_product
