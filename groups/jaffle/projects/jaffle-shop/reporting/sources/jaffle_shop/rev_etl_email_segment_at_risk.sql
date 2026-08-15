-- source extract for rev_etl_email_segment_at_risk (PII columns excluded by the MDL projection)
select customer_id, customer_name, churn_propensity_score, lifetime_spend, last_order_at, total_orders, email_segment, exported_at
from main_marts.rev_etl_email_segment_at_risk
