-- source extract for narrow_loyalty_tier_counts (PII columns excluded by the MDL projection)
select tier_name, member_count
from main_marts.narrow_loyalty_tier_counts
