-- source extract for int_campaign_by_store_performance (PII columns excluded by the MDL projection)
select campaign_id, location_id, redemption_count, total_order_revenue, campaign_name, location_name, total_discount, avg_order_value
from main_marts.int_campaign_by_store_performance
