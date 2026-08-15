-- source extract for adv_latest_review_per_product (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, review_id, reviewer_name, latest_rating, latest_review_title, latest_review_body, latest_review_date, total_reviews, avg_rating, latest_vs_average
from main_marts.adv_latest_review_per_product
