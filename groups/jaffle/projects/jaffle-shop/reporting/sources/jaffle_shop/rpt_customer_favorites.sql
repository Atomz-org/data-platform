-- source extract for rpt_customer_favorites (PII columns excluded by the MDL projection)
select customer_segment, product_id, product_name, product_type, customer_count, total_purchases, avg_share_of_wallet, popularity_rank_in_segment
from main_marts.rpt_customer_favorites
