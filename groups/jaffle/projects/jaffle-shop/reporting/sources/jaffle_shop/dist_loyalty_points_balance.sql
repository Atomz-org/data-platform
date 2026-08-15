-- source extract for dist_loyalty_points_balance (PII columns excluded by the MDL projection)
select points_bucket, member_count, avg_balance, min_balance, max_balance
from main_marts.dist_loyalty_points_balance
