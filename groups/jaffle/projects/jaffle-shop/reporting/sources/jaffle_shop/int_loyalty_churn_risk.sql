-- source extract for int_loyalty_churn_risk (PII columns excluded by the MDL projection)
select loyalty_member_id, days_since_last_transaction, churn_risk_level, is_declining_activity, current_points_balance, total_points_earned, total_points_redeemed, total_transactions, first_transaction_date, last_transaction_date, points_earned_last_90d, points_earned_prior_90d, transactions_last_90d
from main_marts.int_loyalty_churn_risk
