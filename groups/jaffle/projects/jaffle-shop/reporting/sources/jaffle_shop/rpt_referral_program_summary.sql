-- source extract for rpt_referral_program_summary (PII columns excluded by the MDL projection)
select referrer_customer_id, referrer_name, total_referrals_made, successful_referrals, referrer_total_rewards, referral_conversion_rate, referee_total_revenue, referee_total_orders, referrer_roi, referrer_rank
from main_marts.rpt_referral_program_summary
