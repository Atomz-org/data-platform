-- source extract for trend_waste_rate (PII columns excluded by the MDL projection)
select waste_date, location_id, waste_rate_pct, waste_rate_7d_ma, waste_rate_28d_ma, waste_anomaly_flag
from main_marts.trend_waste_rate
