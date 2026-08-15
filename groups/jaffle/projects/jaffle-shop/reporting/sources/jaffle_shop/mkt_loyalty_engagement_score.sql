-- source extract for mkt_loyalty_engagement_score (PII columns excluded by the MDL projection)
select customer_id, loyalty_member_id, current_tier_name, enrolled_at, total_transactions, redemption_count, days_since_last_txn, current_points, engagement_score, engagement_tier
from main_marts.mkt_loyalty_engagement_score
