-- source extract for scr_customer_churn_propensity (PII columns excluded by the MDL projection)
select customer_id, churn_propensity_score, churn_risk_tier, customer_name, days_since_last_order, total_orders, lifetime_spend, rfm_total_score, loyalty_tier, recency_score, frequency_score, loyalty_score, spend_score
from main_marts.scr_customer_churn_propensity
