-- source extract for mkt_coupon_fraud_detection (PII columns excluded by the MDL projection)
select coupon_id, total_redemptions, unique_customers, total_discount_given, avg_discount, usage_spike_days, max_uses_by_single_customer, fraud_risk_flag
from main_marts.mkt_coupon_fraud_detection
