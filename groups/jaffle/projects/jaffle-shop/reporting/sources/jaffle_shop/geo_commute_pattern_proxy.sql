-- source extract for geo_commute_pattern_proxy (PII columns excluded by the MDL projection)
select location_id, store_name, order_hour, order_count, total_orders, pct_of_store_orders, time_period
from main_marts.geo_commute_pattern_proxy
