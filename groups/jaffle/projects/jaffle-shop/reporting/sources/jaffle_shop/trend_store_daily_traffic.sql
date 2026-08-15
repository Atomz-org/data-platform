-- source extract for trend_store_daily_traffic (PII columns excluded by the MDL projection)
select visit_date, location_id, transaction_count, traffic_7d_ma, traffic_28d_ma, wow_change, traffic_band
from main_marts.trend_store_daily_traffic
