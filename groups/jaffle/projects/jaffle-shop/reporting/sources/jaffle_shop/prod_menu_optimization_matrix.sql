-- source extract for prod_menu_optimization_matrix (PII columns excluded by the MDL projection)
select product_id, item_name, category_name, popularity_rank, total_units_sold, gross_margin, gross_margin_pct, matrix_quadrant, recommendation
from main_marts.prod_menu_optimization_matrix
