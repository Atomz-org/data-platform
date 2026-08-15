-- source extract for dist_customer_order_frequency (PII columns excluded by the MDL projection)
select frequency_bucket, customer_count, avg_orders_in_bucket, mean_frequency, median_frequency, p90_frequency
from main_marts.dist_customer_order_frequency
