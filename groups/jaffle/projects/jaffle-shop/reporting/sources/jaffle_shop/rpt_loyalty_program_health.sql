-- source extract for rpt_loyalty_program_health (PII columns excluded by the MDL projection)
select current_tier_name, member_count, active_members, avg_lifetime_points, avg_current_balance, avg_points_earned, avg_points_redeemed, tier_redemption_rate, program_total_members, program_active_members, program_redemption_rate, tier_member_share
from main_marts.rpt_loyalty_program_health
