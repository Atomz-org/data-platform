-- source extract for inc_fct_product_reviews (PII columns excluded by the MDL projection)
select review_id, product_id, customer_id, rating, reviewed_date, review_month, sentiment
from main_marts.inc_fct_product_reviews
