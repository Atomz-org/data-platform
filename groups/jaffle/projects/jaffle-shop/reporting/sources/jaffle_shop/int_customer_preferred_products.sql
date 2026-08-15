-- source extract for int_customer_preferred_products (PII columns excluded by the MDL projection)
select customer_id, top1_product_name, top1_purchase_count, top1_product_id, top1_product_share_pct, top2_product_id, top2_product_name, top2_purchase_count, top3_product_id, top3_product_name, top3_purchase_count, total_items_purchased
from main_marts.int_customer_preferred_products
