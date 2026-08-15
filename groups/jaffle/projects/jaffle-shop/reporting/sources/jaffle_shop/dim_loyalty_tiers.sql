-- source extract for dim_loyalty_tiers (PII columns excluded by the MDL projection)
select tier_id, tier_name, tier_description, minimum_points, maximum_points, points_multiplier, annual_reward, tier_points_range, tier_rank
from main_marts.dim_loyalty_tiers
