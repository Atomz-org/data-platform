-- source extract for trend_revenue_90d_ma (PII columns excluded by the MDL projection)
select revenue_date, location_id, total_revenue, revenue_90d_ma, revenue_90d_min, revenue_90d_max, long_term_trend
from main_marts.trend_revenue_90d_ma
