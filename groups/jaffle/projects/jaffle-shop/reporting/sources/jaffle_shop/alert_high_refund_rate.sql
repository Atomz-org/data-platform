-- source extract for alert_high_refund_rate (PII columns excluded by the MDL projection)
select order_date, location_id, total_orders, refund_count, refund_rate_pct, alert_type, severity
from main_marts.alert_high_refund_rate
