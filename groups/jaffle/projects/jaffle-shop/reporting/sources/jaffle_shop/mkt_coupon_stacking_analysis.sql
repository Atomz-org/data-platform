-- source extract for mkt_coupon_stacking_analysis (PII columns excluded by the MDL projection)
select customer_id, order_id, coupons_used, total_discount, order_total, discount_pct_of_order, stacking_behavior, stacking_severity
from main_marts.mkt_coupon_stacking_analysis
