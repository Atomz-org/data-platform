-- source extract for rpt_customer_journey_summary (PII columns excluded by the MDL projection)
select customer_id, customer_name, acquisition_source, first_order_at, total_orders, is_repeat_customer, is_frequent_buyer, is_loyalty_member, loyalty_enrolled_at, days_to_loyalty_enrollment, loyalty_tier, loyalty_lifecycle_stage, loyalty_points_balance, lifetime_spend, ltv_tier, rfm_total_score, days_since_last_order, customer_tenure_days, preferred_store_name, marketing_engagement_level, campaigns_responded_to, journey_stage
from main_marts.rpt_customer_journey_summary
