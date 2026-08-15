-- source extract for prod_bundle_recommendation (PII columns excluded by the MDL projection)
select product_id_a, product_a_name, product_id_b, product_b_name, co_occurrence_count, affinity_score, combined_margin, bundle_strength, pair_rank
from main_marts.prod_bundle_recommendation
