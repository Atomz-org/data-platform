-- source extract for mkt_loyalty_point_liability (PII columns excluded by the MDL projection)
select total_members_with_balance, total_outstanding_points, total_liability_dollars, avg_points_per_member, avg_liability_per_member, max_points_balance, max_liability_single_member, high_balance_members, high_balance_liability
from main_marts.mkt_loyalty_point_liability
