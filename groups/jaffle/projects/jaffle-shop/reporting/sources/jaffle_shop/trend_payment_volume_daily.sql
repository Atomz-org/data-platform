-- source extract for trend_payment_volume_daily (PII columns excluded by the MDL projection)
select processed_date, payment_method, transaction_count, total_amount, txn_count_7d_ma, amount_7d_ma, txn_same_day_last_week
from main_marts.trend_payment_volume_daily
