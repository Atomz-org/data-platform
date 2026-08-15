-- source extract for int_loyalty_balance_monthly (PII columns excluded by the MDL projection)
select month_start, loyalty_member_id, customer_id, end_of_month_balance, points_earned_in_month, points_redeemed_in_month, transactions_in_month, points_earned_cumulative, points_redeemed_cumulative
from main_marts.int_loyalty_balance_monthly
