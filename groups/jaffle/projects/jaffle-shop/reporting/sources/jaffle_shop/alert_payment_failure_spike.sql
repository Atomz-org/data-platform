-- source extract for alert_payment_failure_spike (PII columns excluded by the MDL projection)
select processed_date, total_payments, failed_payments, failure_rate_pct, alert_type, severity
from main_marts.alert_payment_failure_spike
