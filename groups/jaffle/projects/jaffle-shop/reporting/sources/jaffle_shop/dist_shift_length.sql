-- source extract for dist_shift_length (PII columns excluded by the MDL projection)
select length_bucket, shift_count, avg_hours, mean_length, median_length
from main_marts.dist_shift_length
