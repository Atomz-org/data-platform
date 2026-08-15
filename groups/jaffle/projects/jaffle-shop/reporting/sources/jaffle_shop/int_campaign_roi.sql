-- source extract for int_campaign_roi (PII columns excluded by the MDL projection)
select campaign_id, total_spend, attributed_revenue, roi_ratio, cost_per_order, campaign_name, campaign_channel, attributed_orders, attributed_customers, total_discounts_given, first_spend_date, last_spend_date
from main_marts.int_campaign_roi
