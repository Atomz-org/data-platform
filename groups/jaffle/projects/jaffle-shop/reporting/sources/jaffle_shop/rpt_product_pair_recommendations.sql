-- source extract for rpt_product_pair_recommendations (PII columns excluded by the MDL projection)
select product_id_a, product_name_a, product_type_a, product_id_b, product_name_b, product_type_b, co_occurrence_count, product_a_total_orders, product_b_total_orders, support_a, support_b, affinity_rank, association_lift, recommendation_strength, is_cross_category_pair
from main_marts.rpt_product_pair_recommendations
