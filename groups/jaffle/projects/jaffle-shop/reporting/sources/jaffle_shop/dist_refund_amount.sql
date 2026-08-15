-- source extract for dist_refund_amount (PII columns excluded by the MDL projection)
select refund_bucket, refund_count, bucket_total, mean_refund, median_refund, p90_refund, total_refunds
from main_marts.dist_refund_amount
