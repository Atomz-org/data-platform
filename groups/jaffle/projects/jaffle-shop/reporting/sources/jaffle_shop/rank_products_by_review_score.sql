-- source extract for rank_products_by_review_score (PII columns excluded by the MDL projection)
select product_id, review_count, avg_rating, positive_count, positive_pct, rating_rank, rating_quintile
from main_marts.rank_products_by_review_score
