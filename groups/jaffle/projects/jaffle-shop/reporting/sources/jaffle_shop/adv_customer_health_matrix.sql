-- source extract for adv_customer_health_matrix (PII columns excluded by the MDL projection)
select customer_id, days_since_last_order, order_count, total_spend, recency_score, frequency_score, monetary_score, rfm_total_score, recency_tier, frequency_tier, monetary_tier, health_segment, health_label, recommended_action
from main_marts.adv_customer_health_matrix
