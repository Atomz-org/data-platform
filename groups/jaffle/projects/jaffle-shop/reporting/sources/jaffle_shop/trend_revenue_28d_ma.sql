-- source extract for trend_revenue_28d_ma (PII columns excluded by the MDL projection)
select revenue_date, location_id, total_revenue, revenue_28d_ma, revenue_28d_stddev, anomaly_flag
from main_marts.trend_revenue_28d_ma
