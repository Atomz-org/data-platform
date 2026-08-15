-- source extract for view_cmo_channel_performance (PII columns excluded by the MDL projection)
select channel, attributed_revenue, channel_spend, attributed_customers, roas, cost_per_acquisition
from main_marts.view_cmo_channel_performance
