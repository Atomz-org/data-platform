-- source extract for rev_etl_loyalty_sync (PII columns excluded by the MDL projection)
select loyalty_member_id, customer_id, current_tier_name, current_points_balance, enrolled_at, membership_status, synced_at, source_system
from main_marts.rev_etl_loyalty_sync
