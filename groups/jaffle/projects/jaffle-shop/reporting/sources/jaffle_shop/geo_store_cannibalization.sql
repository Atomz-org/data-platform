-- source extract for geo_store_cannibalization (PII columns excluded by the MDL projection)
select store_a_id, store_a_name, store_b_id, store_b_name, shared_customers, store_a_total_customers, store_b_total_customers, store_a_overlap_pct, store_b_overlap_pct, cannibalization_risk
from main_marts.geo_store_cannibalization
