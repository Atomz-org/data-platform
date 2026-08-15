-- source extract for int_combo_meal_analysis (PII columns excluded by the MDL projection)
select product_a, product_b, co_occurrence_count, product_a_orders, product_b_orders, pct_of_product_a_orders, pct_of_product_b_orders
from main_marts.int_combo_meal_analysis
