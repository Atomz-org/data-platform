-- source extract for geo_store_revenue_potential (PII columns excluded by the MDL projection)
select location_id, store_name, current_avg_revenue, fleet_avg_revenue, p75_revenue, p90_revenue, gap_to_p75, gap_to_p90, potential_classification
from main_marts.geo_store_revenue_potential
