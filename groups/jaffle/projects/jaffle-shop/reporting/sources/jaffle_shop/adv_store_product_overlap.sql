-- source extract for adv_store_product_overlap (PII columns excluded by the MDL projection)
select store_a_id, store_a_name, store_a_product_count, store_b_id, store_b_name, store_b_product_count, shared_product_count, has_overlap, jaccard_similarity, unique_to_store_a, unique_to_store_b
from main_marts.adv_store_product_overlap
