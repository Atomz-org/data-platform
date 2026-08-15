-- source extract for trend_aov_monthly (PII columns excluded by the MDL projection)
select month_start, location_id, monthly_revenue, monthly_orders, aov, aov_3m_ma, prev_month_aov, trend_direction
from main_marts.trend_aov_monthly
