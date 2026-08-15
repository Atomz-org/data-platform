-- source extract for geo_store_trade_area (PII columns excluded by the MDL projection)
select location_id, store_name, store_location_id, nearest_store_id, nearest_store_name, nearest_store_distance_proxy, trade_area_overlap_risk
from main_marts.geo_store_trade_area
