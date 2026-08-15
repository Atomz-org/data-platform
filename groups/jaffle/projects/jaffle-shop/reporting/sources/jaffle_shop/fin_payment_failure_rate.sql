-- source extract for fin_payment_failure_rate (PII columns excluded by the MDL projection)
select processed_date, payment_method, total_attempts, successful, failed, declined, other_status, failed_amount, total_attempted_amount, failure_rate_pct, failed_amount_pct
from main_marts.fin_payment_failure_rate
