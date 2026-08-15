-- source extract for dist_order_value (PII columns excluded by the MDL projection)
select value_bucket, order_count, bucket_avg, mean_value, p50_median, p25, p75, p90, p95, total_orders
from main_marts.dist_order_value
