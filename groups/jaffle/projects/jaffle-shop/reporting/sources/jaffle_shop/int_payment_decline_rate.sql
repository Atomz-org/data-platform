-- source extract for int_payment_decline_rate (PII columns excluded by the MDL projection)
select location_id, payment_method, decline_rate_pct, processed_date, total_attempts, successful_payments, declined_payments
from main_marts.int_payment_decline_rate
