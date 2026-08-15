-- source extract for int_loyalty_points_velocity (PII columns excluded by the MDL projection)
select loyalty_member_id, points_month, points_earned, points_redeemed, rolling_3m_avg_earned, net_points, transaction_count, monthly_activity_type
from main_marts.int_loyalty_points_velocity
