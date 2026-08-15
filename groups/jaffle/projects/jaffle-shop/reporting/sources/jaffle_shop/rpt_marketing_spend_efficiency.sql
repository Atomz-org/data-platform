-- source extract for rpt_marketing_spend_efficiency (PII columns excluded by the MDL projection)
select month, marketing_spend, revenue, order_count, unique_customers, active_spend_days, channels_used, spend_to_revenue_ratio, revenue_per_spend_dollar, cost_per_order, cost_per_customer
from main_marts.rpt_marketing_spend_efficiency
