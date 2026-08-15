-- source extract for mkt_customer_next_best_action (PII columns excluded by the MDL projection)
select customer_id, lifecycle_stage, total_orders, days_since_last_order, lifetime_spend, preferred_channel, next_best_action, action_urgency
from main_marts.mkt_customer_next_best_action
