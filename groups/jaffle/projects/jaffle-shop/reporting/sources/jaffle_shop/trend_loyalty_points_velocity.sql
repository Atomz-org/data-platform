-- source extract for trend_loyalty_points_velocity (PII columns excluded by the MDL projection)
select transacted_at, points_earned, points_redeemed, net_points, active_members, earned_7d_ma, redeemed_7d_ma, net_points_28d_ma, points_flow_status
from main_marts.trend_loyalty_points_velocity
