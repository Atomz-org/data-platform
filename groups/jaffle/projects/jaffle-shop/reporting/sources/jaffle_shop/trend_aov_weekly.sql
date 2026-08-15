-- source extract for trend_aov_weekly (PII columns excluded by the MDL projection)
select week_start, location_id, weekly_revenue, weekly_orders, aov, aov_4w_ma, aov_wow_change
from main_marts.trend_aov_weekly
