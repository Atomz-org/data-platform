-- source extract for int_payment_method_by_segment (PII columns excluded by the MDL projection)
select rfm_segment, payment_method, pct_of_segment_transactions, transaction_count, total_amount, avg_amount
from main_marts.int_payment_method_by_segment
