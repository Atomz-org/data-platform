-- source extract for int_average_transaction_value (PII columns excluded by the MDL projection)
select location_id, transaction_date, avg_transaction_value, rolling_7d_avg_atv, rolling_30d_avg_atv, daily_order_count, daily_total_revenue, min_transaction_value, max_transaction_value
from main_marts.int_average_transaction_value
