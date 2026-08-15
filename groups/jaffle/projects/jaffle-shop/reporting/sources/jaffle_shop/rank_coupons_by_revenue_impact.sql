-- source extract for rank_coupons_by_revenue_impact (PII columns excluded by the MDL projection)
select coupon_id, redemptions, total_discount, associated_revenue, net_revenue_impact, revenue_impact_rank
from main_marts.rank_coupons_by_revenue_impact
