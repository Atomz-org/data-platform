-- source extract for rpt_loyalty_tier_migration (PII columns excluded by the MDL projection)
select activity_month, previous_month_tier, current_month_tier, transition_type, member_count
from main_marts.rpt_loyalty_tier_migration
