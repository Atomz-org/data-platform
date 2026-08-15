-- source extract for alert_customer_churn_spike (PII columns excluded by the MDL projection)
select month_start, tracked_active_customers, churned_customers, churn_rate_pct, churn_3m_avg, alert_type, severity
from main_marts.alert_customer_churn_spike
