-- source extract for rpt_360_customer_health_dashboard (PII columns excluded by the MDL projection)
select total_customers, high_risk_customers, avg_churn_score, medium_risk_customers, low_risk_customers, avg_lifetime_spend, avg_orders_per_customer, avg_churn_propensity_score
from main_marts.rpt_360_customer_health_dashboard
