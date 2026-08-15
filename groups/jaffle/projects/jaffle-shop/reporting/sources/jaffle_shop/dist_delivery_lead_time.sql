-- source extract for dist_delivery_lead_time (PII columns excluded by the MDL projection)
select lead_time_bucket, delivery_count, mean_lead_time, median_lead_time, p90_lead_time
from main_marts.dist_delivery_lead_time
