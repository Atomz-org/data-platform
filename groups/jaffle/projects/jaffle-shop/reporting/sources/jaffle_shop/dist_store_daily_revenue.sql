-- source extract for dist_store_daily_revenue (PII columns excluded by the MDL projection)
select location_id, active_days, mean_daily_rev, p25_rev, median_rev, p75_rev, p90_rev, min_rev, max_rev
from main_marts.dist_store_daily_revenue
