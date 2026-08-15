-- source extract for poc_coupon_usage_mom (PII columns excluded by the MDL projection)
select redemption_month, current_redemptions, prior_month_redemptions, current_discount, prior_month_discount, redemptions_mom_pct, discount_mom_pct
from main_marts.poc_coupon_usage_mom
