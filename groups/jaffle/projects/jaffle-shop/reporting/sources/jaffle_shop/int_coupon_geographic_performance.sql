-- source extract for int_coupon_geographic_performance (PII columns excluded by the MDL projection)
select location_id, discount_type, total_redemptions, location_name, total_discount_given, avg_discount_per_redemption, unique_customers_redeeming, distinct_coupons_used
from main_marts.int_coupon_geographic_performance
