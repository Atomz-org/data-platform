-- source extract for geo_store_saturation_index (PII columns excluded by the MDL projection)
select area_proxy, stores_in_area, area_monthly_revenue, area_avg_revenue_per_store, optimal_revenue_per_store, saturation_index, saturation_status
from main_marts.geo_store_saturation_index
