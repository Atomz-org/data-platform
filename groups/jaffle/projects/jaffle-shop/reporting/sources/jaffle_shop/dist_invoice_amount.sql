-- source extract for dist_invoice_amount (PII columns excluded by the MDL projection)
select amount_bucket, invoice_count, avg_amount, min_amount, max_amount
from main_marts.dist_invoice_amount
