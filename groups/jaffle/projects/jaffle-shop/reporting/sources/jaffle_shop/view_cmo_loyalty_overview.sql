-- source extract for view_cmo_loyalty_overview (PII columns excluded by the MDL projection)
select current_tier_name, member_count, active_members, program_total_members, program_active_members, redemption_rate_pct, active_member_pct, program_engagement_level
from main_marts.view_cmo_loyalty_overview
