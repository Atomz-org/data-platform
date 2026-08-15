-- source extract for dist_coupon_discount (PII columns excluded by the MDL projection)
select discount_bucket, redemption_count, mean_discount, median_discount, p75_discount
from main_marts.dist_coupon_discount
