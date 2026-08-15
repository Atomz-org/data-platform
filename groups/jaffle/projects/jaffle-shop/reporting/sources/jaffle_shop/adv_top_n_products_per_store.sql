-- source extract for adv_top_n_products_per_store (PII columns excluded by the MDL projection)
select location_id, location_name, product_id, product_name, total_revenue, units_sold, product_rank
from main_marts.adv_top_n_products_per_store
