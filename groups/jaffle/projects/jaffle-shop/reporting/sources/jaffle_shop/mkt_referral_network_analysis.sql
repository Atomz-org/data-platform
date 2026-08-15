-- source extract for mkt_referral_network_analysis (PII columns excluded by the MDL projection)
select referrer_customer_id, total_referrals, max_chain_depth, first_referral_date, last_referral_date, total_referred_revenue, avg_revenue_per_referral, referrer_tier
from main_marts.mkt_referral_network_analysis
