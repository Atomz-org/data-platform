-- source extract for wide_loyalty_member_summary (PII columns excluded by the MDL projection)
select loyalty_member_id, customer_id, customer_name, current_tier_name, enrolled_at, membership_status, current_points_balance, total_points_earned, total_points_redeemed, lifetime_spend, total_orders, loyalty_churn_risk, churn_risk_tier
from main_marts.wide_loyalty_member_summary
