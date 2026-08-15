-- source extract for dist_maintenance_cost (PII columns excluded by the MDL projection)
select cost_bucket, event_count, bucket_total, mean_cost, median_cost, p75_cost
from main_marts.dist_maintenance_cost
