-- source extract for int_customer_first_purchase_context (PII columns excluded by the MDL projection)
select customer_id, first_order_id, first_order_date, first_store_name, first_order_total, first_order_distinct_products, first_order_day_name, first_order_is_weekend, first_store_id, first_order_subtotal, first_order_total_items, first_product_name, first_order_day_of_week
from main_marts.int_customer_first_purchase_context
