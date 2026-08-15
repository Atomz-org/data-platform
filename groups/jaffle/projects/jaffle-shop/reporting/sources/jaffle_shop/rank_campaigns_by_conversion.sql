-- source extract for rank_campaigns_by_conversion (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, active_spend_days, total_spend, efficiency, conversion_rank, conversion_quartile
from main_marts.rank_campaigns_by_conversion
