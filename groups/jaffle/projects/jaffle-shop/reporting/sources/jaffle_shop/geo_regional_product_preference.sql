-- source extract for geo_regional_product_preference (PII columns excluded by the MDL projection)
select location_id, store_name, product_id, total_quantity, total_sales, store_total_sales, sales_mix_pct, product_rank
from main_marts.geo_regional_product_preference
