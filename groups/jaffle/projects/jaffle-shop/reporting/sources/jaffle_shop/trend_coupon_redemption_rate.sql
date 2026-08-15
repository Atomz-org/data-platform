-- source extract for trend_coupon_redemption_rate (PII columns excluded by the MDL projection)
select metric_date, redemption_rate_pct, redemptions, total_orders, total_discount, rate_7d_ma, rate_28d_ma
from main_marts.trend_coupon_redemption_rate
