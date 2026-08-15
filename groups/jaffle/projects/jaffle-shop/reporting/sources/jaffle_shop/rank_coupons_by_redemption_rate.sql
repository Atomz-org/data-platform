-- source extract for rank_coupons_by_redemption_rate (PII columns excluded by the MDL projection)
select coupon_id, redemption_count, total_discount, avg_discount, redemption_rank, redemption_quartile
from main_marts.rank_coupons_by_redemption_rate
