-- source extract for geo_store_expansion_candidates (PII columns excluded by the MDL projection)
select location_id, store_name, store_health_score, revenue_growth_score, profitability_score, expansion_recommendation
from main_marts.geo_store_expansion_candidates
