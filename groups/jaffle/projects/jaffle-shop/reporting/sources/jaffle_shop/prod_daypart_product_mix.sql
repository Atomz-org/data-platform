-- source extract for prod_daypart_product_mix (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, daypart, total_quantity, total_revenue, daypart_rank, daypart_share_pct
from main_marts.prod_daypart_product_mix
