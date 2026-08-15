-- source extract for mkt_channel_mix_optimization (PII columns excluded by the MDL projection)
select campaign_channel, campaigns_count, total_spend, total_revenue, avg_roi_pct, overall_roas, current_spend_share_pct, investment_recommendation
from main_marts.mkt_channel_mix_optimization
