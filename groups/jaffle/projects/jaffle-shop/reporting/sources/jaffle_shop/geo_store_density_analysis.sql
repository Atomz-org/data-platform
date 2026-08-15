-- source extract for geo_store_density_analysis (PII columns excluded by the MDL projection)
select region_proxy, store_count, avg_store_monthly_revenue, total_region_revenue, revenue_per_store
from main_marts.geo_store_density_analysis
