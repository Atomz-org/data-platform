-- source extract for rpt_review_sentiment_by_product (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, total_review_count, avg_rating, min_rating, max_rating, positive_review_count, neutral_review_count, negative_review_count, positive_review_pct, negative_review_pct, first_review_date, last_review_date, latest_month_avg_rating, latest_month_review_count, prev_month_avg_rating, rating_trend, overall_sentiment, rating_trend_direction
from main_marts.rpt_review_sentiment_by_product
