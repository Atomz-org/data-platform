-- source extract for fct_loyalty_transactions (PII columns excluded by the MDL projection)
select loyalty_transaction_id, loyalty_member_id, order_id, transaction_type, transaction_description, points, transacted_at, customer_id, membership_status, current_tier_id, enrolled_at, running_points_balance
from main_marts.fct_loyalty_transactions
