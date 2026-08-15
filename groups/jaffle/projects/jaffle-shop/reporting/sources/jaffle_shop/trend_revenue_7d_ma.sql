-- source extract for trend_revenue_7d_ma (PII columns excluded by the MDL projection)
select revenue_date, location_id, total_revenue, revenue_7d_ma, deviation_from_7d_ma, anomaly_flag
from main_marts.trend_revenue_7d_ma
