-- source extract for rpt_churn_risk_dashboard (PII columns excluded by the MDL projection)
select customer_id, customer_name, lifetime_spend, total_orders, days_since_last_order, rfm_total_score, ltv_tier, loyalty_tier, loyalty_points_balance, preferred_store_name, marketing_engagement_level, orders_last_6_months, orders_prior_6_months, order_frequency_change, churn_risk_level, customer_value_priority, recommended_action
from main_marts.rpt_churn_risk_dashboard
