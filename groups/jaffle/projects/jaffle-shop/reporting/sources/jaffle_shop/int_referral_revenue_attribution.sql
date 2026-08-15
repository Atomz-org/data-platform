-- source extract for int_referral_revenue_attribution (PII columns excluded by the MDL projection)
select referrer_customer_id, total_attributed_revenue, net_referral_revenue, total_referees, total_referrals, referee_order_count, total_rewards_paid
from main_marts.int_referral_revenue_attribution
