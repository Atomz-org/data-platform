-- source extract for int_new_vs_returning_product_mix (PII columns excluded by the MDL projection)
select product_id, customer_type, item_count, total_revenue, order_count, customer_count
from main_marts.int_new_vs_returning_product_mix
