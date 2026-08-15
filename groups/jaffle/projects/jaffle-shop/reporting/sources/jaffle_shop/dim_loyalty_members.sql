-- source extract for dim_loyalty_members (PII columns excluded by the MDL projection)
select loyalty_member_id, customer_id, membership_status, lifetime_points, enrolled_at, last_activity_at, current_tier_name, current_multiplier, earned_tier_name, next_tier_name, points_to_next_tier, current_points_balance, total_points_earned, total_points_redeemed, is_active_member, is_tier_mismatched
from main_marts.dim_loyalty_members
