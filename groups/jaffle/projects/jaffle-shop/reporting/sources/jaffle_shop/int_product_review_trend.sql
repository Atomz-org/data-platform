-- source extract for int_product_review_trend (PII columns excluded by the MDL projection)
select product_id, review_month, avg_rating, rolling_3m_avg_rating, rating_tier, review_count, min_rating, max_rating, positive_reviews, negative_reviews
from main_marts.int_product_review_trend
