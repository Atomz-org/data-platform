-- source extract for narrow_top_10_products (PII columns excluded by the MDL projection)
select product_id, product_name, total_revenue
from main_marts.narrow_top_10_products
