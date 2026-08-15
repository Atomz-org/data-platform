-- source extract for stg_derived_review_with_product (PII columns excluded by the MDL projection)
select review_id, product_id, product_name, product_type, customer_id, rating, reviewed_date, review_title, review_body
from main_marts.stg_derived_review_with_product
