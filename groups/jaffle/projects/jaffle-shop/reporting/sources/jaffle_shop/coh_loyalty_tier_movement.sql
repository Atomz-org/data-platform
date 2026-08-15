-- source extract for coh_loyalty_tier_movement (PII columns excluded by the MDL projection)
select activity_month, tier_name, member_count, maintained_count, upgrade_pending_count
from main_marts.coh_loyalty_tier_movement
