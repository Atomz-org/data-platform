-- source extract for kpi_coupon_redemption_rate (PII columns excluded by the MDL projection)
select order_month, redemptions, total_orders, redemption_rate_pct, total_discount
from main_marts.kpi_coupon_redemption_rate
