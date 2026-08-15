-- source extract for dist_waste_event_cost (PII columns excluded by the MDL projection)
select cost_bucket, event_count, bucket_total, mean_cost, median_cost, p90_cost, total_events
from main_marts.dist_waste_event_cost
