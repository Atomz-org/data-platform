-- source extract for rpt_campaign_effectiveness (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, campaign_channel, total_spend, attributed_orders, attributed_customers, attributed_revenue, total_discounts_given, roi_ratio, cost_per_order, first_spend_date, last_spend_date, effectiveness_tier, net_profit, revenue_per_customer
from main_marts.rpt_campaign_effectiveness
