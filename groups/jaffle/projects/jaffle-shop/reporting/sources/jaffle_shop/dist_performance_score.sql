-- source extract for dist_performance_score (PII columns excluded by the MDL projection)
select overall_score_bucket, review_count, avg_in_bucket, mean_overall_score, median_overall_score
from main_marts.dist_performance_score
