-- source extract for sum_quarterly_loyalty_totals (PII columns excluded by the MDL projection)
select txn_quarter, avg_monthly_members, quarterly_points_earned, quarterly_points_redeemed
from main_marts.sum_quarterly_loyalty_totals
