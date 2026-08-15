-- source extract for mkt_customer_journey_touchpoints (PII columns excluded by the MDL projection)
select customer_id, touchpoint_date, channel, touchpoint_type, campaign_id, touchpoint_sequence
from main_marts.mkt_customer_journey_touchpoints
