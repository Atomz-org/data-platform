-- source extract for rpt_customer_reactivation (PII columns excluded by the MDL projection)
select customer_id, customer_name, customer_type, lifetime_spend, count_lifetime_orders, order_id, reactivation_date, days_since_previous_order, campaign_id, campaign_name, campaign_channel, discount_applied, reactivation_driver
from main_marts.rpt_customer_reactivation
