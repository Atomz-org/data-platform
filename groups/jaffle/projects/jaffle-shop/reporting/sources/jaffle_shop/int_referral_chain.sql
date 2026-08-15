-- source extract for int_referral_chain (PII columns excluded by the MDL projection)
select referral_id, referrer_customer_id, referee_customer_id, referral_conversion_rate, referral_code, referral_status, referred_at, converted_at, reward_amount, campaign_id, referrer_name, referee_name, total_referrals_made, successful_referrals, referrer_total_rewards
from main_marts.int_referral_chain
