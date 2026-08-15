-- source extract for int_customer_loyalty_enriched (PII columns excluded by the MDL projection)
select customer_id, current_tier, loyalty_points_balance, loyalty_lifecycle_stage, customer_name, member_id, loyalty_enrolled_at, membership_tenure_days, last_tier_before_current, last_tier_change_date, months_in_previous_tier
from main_marts.int_customer_loyalty_enriched
