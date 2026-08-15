-- source extract for dist_inventory_days_on_hand (PII columns excluded by the MDL projection)
select doh_bucket, item_count, mean_doh, median_doh, p75_doh
from main_marts.dist_inventory_days_on_hand
