-- source extract for mkt_attribution_multi_touch (PII columns excluded by the MDL projection)
select channel, campaign_id, attributed_orders, linear_attributed_revenue, position_attributed_revenue, total_touchpoints
from main_marts.mkt_attribution_multi_touch
