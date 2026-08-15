-- source extract for mkt_retention_driver_analysis (PII columns excluded by the MDL projection)
select customer_id, rfm_segment, total_orders, days_since_last_order, lifetime_spend, avg_order_value, recency_score, frequency_score, monetary_score, is_loyalty_member, loyalty_tier, retention_status, loyalty_factor, high_frequency_factor, high_value_factor, recent_engagement_factor
from main_marts.mkt_retention_driver_analysis
