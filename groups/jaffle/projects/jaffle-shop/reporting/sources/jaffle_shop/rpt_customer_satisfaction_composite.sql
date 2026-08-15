-- source extract for rpt_customer_satisfaction_composite (PII columns excluded by the MDL projection)
select customer_id, satisfaction_score, satisfaction_tier, total_orders, refund_rate_pct, avg_review_rating, review_count, days_active
from main_marts.rpt_customer_satisfaction_composite
