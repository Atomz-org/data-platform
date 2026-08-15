-- source extract for geo_foot_traffic_proxy (PII columns excluded by the MDL projection)
select location_id, store_name, order_hour, days_with_traffic, total_orders, avg_daily_orders, peak_daily_orders, traffic_level
from main_marts.geo_foot_traffic_proxy
