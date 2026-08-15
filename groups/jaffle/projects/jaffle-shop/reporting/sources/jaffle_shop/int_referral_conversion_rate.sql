-- source extract for int_referral_conversion_rate (PII columns excluded by the MDL projection)
select total_referrals, status_conversion_rate, purchase_conversion_rate, referral_program_roi, status_converted, referees_who_purchased, converted_and_purchased, total_referee_revenue, total_rewards_paid
from main_marts.int_referral_conversion_rate
