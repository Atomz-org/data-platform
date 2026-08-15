-- source extract for trend_repeat_purchase_rate (PII columns excluded by the MDL projection)
select activity_date, active_customers, new_customers, returning_customers, repeat_rate_pct, repeat_rate_7d_ma, repeat_rate_28d_ma, retention_band
from main_marts.trend_repeat_purchase_rate
