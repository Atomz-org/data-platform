-- source extract for rpt_loyalty_churn_dashboard (PII columns excluded by the MDL projection)
select loyalty_member_id, customer_id, membership_status, current_tier_name, enrolled_at, last_activity_at, lifetime_points, total_points_earned, total_points_redeemed, current_points_balance, last_transaction_date, days_since_last_transaction, points_earned_last_90d, points_earned_prior_90d, transactions_last_90d, is_declining_activity, churn_risk_level, risk_level_member_count, risk_level_total_points_at_risk
from main_marts.rpt_loyalty_churn_dashboard
