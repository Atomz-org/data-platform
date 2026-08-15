-- source extract for alert_refund_spike_daily (PII columns excluded by the MDL projection)
select requested_date, refund_count, total_amount, avg_7d_refunds, pct_of_avg, alert_type, severity
from main_marts.alert_refund_spike_daily
