-- source extract for int_product_affinity (PII columns excluded by the MDL projection)
select product_id_a, product_id_b, co_occurrence_count, support_a, support_b, affinity_rank, product_a_total_orders, product_b_total_orders
from main_marts.int_product_affinity
