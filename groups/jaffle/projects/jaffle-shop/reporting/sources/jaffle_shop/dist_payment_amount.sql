-- source extract for dist_payment_amount (PII columns excluded by the MDL projection)
select payment_method, txn_count, mean_amount, median_amount, p75_amount, p90_amount, p99_amount
from main_marts.dist_payment_amount
