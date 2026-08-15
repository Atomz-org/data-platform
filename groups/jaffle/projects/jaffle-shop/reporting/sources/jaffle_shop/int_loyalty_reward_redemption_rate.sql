-- source extract for int_loyalty_reward_redemption_rate (PII columns excluded by the MDL projection)
select loyalty_member_id, redemption_rate_pct, redemption_behavior, total_points_earned, total_points_redeemed, points_outstanding, earn_transactions, redeem_transactions
from main_marts.int_loyalty_reward_redemption_rate
