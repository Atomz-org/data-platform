-- source extract for alert_new_customer_decline (PII columns excluded by the MDL projection)
select metric_week, new_customers, new_cust_4w_avg, decline_pct, alert_type, severity
from main_marts.alert_new_customer_decline
