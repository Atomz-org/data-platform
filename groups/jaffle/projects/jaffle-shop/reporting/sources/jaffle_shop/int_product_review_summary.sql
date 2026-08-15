-- source extract for int_product_review_summary (PII columns excluded by the MDL projection)
select product_id, total_review_count, avg_rating, positive_review_count, neutral_review_count, negative_review_count, positive_review_pct, negative_review_pct, first_review_date, last_review_date, min_rating, max_rating
from main_marts.int_product_review_summary
