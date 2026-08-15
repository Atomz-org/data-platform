-- source extract for met_monthly_marketing_metrics (PII columns excluded by the MDL projection)
select month_start, total_marketing_spend, coupon_redemptions, channels_used, total_campaign_days, active_loyalty_members, loyalty_earn_events, loyalty_redeem_events, points_earned, points_redeemed, total_discount_given, customers_using_coupons
from main_marts.met_monthly_marketing_metrics
