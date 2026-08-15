-- source extract for int_product_shelf_life_proxy (PII columns excluded by the MDL projection)
select product_id, avg_days_between_sales, freshness_tier, product_name, product_type, max_gap_days
from main_marts.int_product_shelf_life_proxy
