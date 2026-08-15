-- source extract for int_customer_rfm_scores (PII columns excluded by the MDL projection)
select customer_id, recency_score, frequency_score, monetary_score, rfm_total_score, rfm_segment_code, days_since_last_order, order_count, total_spend
from main_marts.int_customer_rfm_scores
