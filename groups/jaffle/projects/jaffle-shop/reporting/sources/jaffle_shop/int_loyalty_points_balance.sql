-- source extract for int_loyalty_points_balance (PII columns excluded by the MDL projection)
select loyalty_member_id, current_points_balance, total_points_earned, total_points_redeemed, total_points_expired, total_bonus_points, total_transactions, first_transaction_date, last_transaction_date
from main_marts.int_loyalty_points_balance
