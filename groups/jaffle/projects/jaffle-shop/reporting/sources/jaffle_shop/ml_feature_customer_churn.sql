-- source extract for ml_feature_customer_churn (PII columns excluded by the MDL projection)
select customer_id, days_since_last_order, lifetime_order_count, lifetime_spend, rfm_total_score, is_loyalty_member, order_trend_slope, churn_label_proxy, recency_score, frequency_score, orders_per_month, avg_order_value, monetary_score, rfm_segment_code, loyalty_tier, loyalty_points_balance, distinct_stores_visited, coupons_redeemed, marketing_engagement_level, recent_3m_order_avg, prior_3m_order_avg, customer_tenure_days
from main_marts.ml_feature_customer_churn
