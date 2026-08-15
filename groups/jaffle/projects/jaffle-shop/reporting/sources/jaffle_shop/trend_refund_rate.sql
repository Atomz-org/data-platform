-- source extract for trend_refund_rate (PII columns excluded by the MDL projection)
select metric_date, refund_rate_pct, refund_value_rate_pct, refund_count, refund_rate_7d_ma, refund_rate_28d_ma, refund_anomaly
from main_marts.trend_refund_rate
