-- source extract for trend_loyalty_enrollment (PII columns excluded by the MDL projection)
select transacted_at, active_earners, active_members, members_7d_ma, members_28d_ma, members_7d_total, same_day_last_week
from main_marts.trend_loyalty_enrollment
