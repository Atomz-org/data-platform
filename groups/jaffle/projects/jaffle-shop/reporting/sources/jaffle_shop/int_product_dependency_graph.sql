-- source extract for int_product_dependency_graph (PII columns excluded by the MDL projection)
select product_a, product_b, shared_ingredient_count, ingredient_overlap_pct, product_a_ingredients, product_b_ingredients
from main_marts.int_product_dependency_graph
