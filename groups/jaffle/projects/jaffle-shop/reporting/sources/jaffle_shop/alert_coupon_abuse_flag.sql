-- source extract for alert_coupon_abuse_flag (PII columns excluded by the MDL projection)
select customer_id, total_redemptions, total_discount, redemptions_per_month, alert_type, severity
from main_marts.alert_coupon_abuse_flag
