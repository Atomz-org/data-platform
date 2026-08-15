-- source extract for geo_store_lifecycle_stage (PII columns excluded by the MDL projection)
select location_id, store_name, months_of_data, avg_revenue, recent_3m_avg, prior_3m_avg, growth_pct, lifecycle_stage
from main_marts.geo_store_lifecycle_stage
