-- source extract for int_campaign_orders (PII columns excluded by the MDL projection)
select campaign_id, order_id, campaign_name, campaign_channel, customer_id, order_total, subtotal, redemption_id, discount_applied, ordered_at
from main_marts.int_campaign_orders
