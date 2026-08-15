-- source extract for adv_store_affinity_network (PII columns excluded by the MDL projection)
select store_a_id, store_a_name, store_b_id, store_b_name, shared_customers, store_a_total_customers, store_b_total_customers, union_customers, affinity_score, overlap_coefficient
from main_marts.adv_store_affinity_network
