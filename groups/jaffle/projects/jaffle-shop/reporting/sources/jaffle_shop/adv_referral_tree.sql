-- source extract for adv_referral_tree (PII columns excluded by the MDL projection)
select root_referrer_id, current_member_id, depth, chain_path, total_chain_revenue
from main_marts.adv_referral_tree
