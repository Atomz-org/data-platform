-- source extract for kpi_loyalty_redemption_rate (PII columns excluded by the MDL projection)
select txn_month, points_earned, points_redeemed, redemption_rate_pct
from main_marts.kpi_loyalty_redemption_rate
