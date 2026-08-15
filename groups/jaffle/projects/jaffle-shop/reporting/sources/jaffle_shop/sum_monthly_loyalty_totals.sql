-- source extract for sum_monthly_loyalty_totals (PII columns excluded by the MDL projection)
select txn_month, active_members, points_earned, points_redeemed, net_points, total_transactions
from main_marts.sum_monthly_loyalty_totals
