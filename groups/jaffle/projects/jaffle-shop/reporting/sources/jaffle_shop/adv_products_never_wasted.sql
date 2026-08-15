-- source extract for adv_products_never_wasted (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, product_price, waste_category
from main_marts.adv_products_never_wasted
