-- source extract for stg_derived_loyalty_with_tier (PII columns excluded by the MDL projection)
select loyalty_member_id, customer_id, current_tier_id, tier_name, minimum_points, maximum_points, enrolled_at, membership_status
from main_marts.stg_derived_loyalty_with_tier
