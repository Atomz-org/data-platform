-- source extract for rank_campaigns_by_reach (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, reach_proxy, total_spend, channel_count, reach_rank, reach_quartile
from main_marts.rank_campaigns_by_reach
