-- source extract for adv_latest_price_per_product (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, current_price, previous_price, last_change_reason, last_price_change_date, price_change_amount, price_change_pct
from main_marts.adv_latest_price_per_product
