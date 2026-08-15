-- source extract for int_customer_channel_affinity (PII columns excluded by the MDL projection)
select customer_id, channel, channel_rank, channel_pct, engagement_count, total_engagements
from main_marts.int_customer_channel_affinity
