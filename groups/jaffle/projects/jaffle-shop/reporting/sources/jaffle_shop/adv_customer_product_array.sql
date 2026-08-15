-- source extract for adv_customer_product_array (PII columns excluded by the MDL projection)
select customer_id, customer_name, products_purchased, product_names_purchased, product_types_purchased, unique_product_count, total_items_purchased, total_orders, avg_items_per_order, product_diversity_ratio
from main_marts.adv_customer_product_array
