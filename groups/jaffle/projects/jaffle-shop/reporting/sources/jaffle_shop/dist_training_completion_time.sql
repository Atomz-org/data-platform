-- source extract for dist_training_completion_time (PII columns excluded by the MDL projection)
select duration_bucket, completion_count, mean_days, median_days, p75_days
from main_marts.dist_training_completion_time
