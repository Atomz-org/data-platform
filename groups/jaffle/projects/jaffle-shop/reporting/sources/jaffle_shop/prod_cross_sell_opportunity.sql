-- source extract for prod_cross_sell_opportunity (PII columns excluded by the MDL projection)
select product_id_a, product_a_name, product_id_b, product_b_name, co_occurrence_count, support_a, opportunity_level
from main_marts.prod_cross_sell_opportunity
