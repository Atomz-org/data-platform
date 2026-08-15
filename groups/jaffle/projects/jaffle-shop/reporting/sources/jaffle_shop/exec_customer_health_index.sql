-- source extract for exec_customer_health_index (PII columns excluded by the MDL projection)
select reporting_month, customer_health_index, active_pct, high_risk_pct, total_tracked_customers, tracked_active_customers, dormant_customers, churned_customers, churn_pct, new_customers, total_orders, total_revenue, mom_customer_visit_change, total_scored_customers, avg_churn_score, high_risk_count, medium_risk_count, low_risk_count
from main_marts.exec_customer_health_index
