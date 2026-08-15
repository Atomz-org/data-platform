-- source extract for int_loyalty_tier_progression (PII columns excluded by the MDL projection)
select loyalty_member_id, customer_id, current_tier_name, earned_tier_name, points_to_next_tier, membership_status, enrolled_at, last_activity_at, lifetime_points, current_points_balance, total_points_earned, total_points_redeemed, current_tier_id, current_multiplier, earned_tier_id, next_tier_id, next_tier_name, next_tier_min_points
from main_marts.int_loyalty_tier_progression
