-- source extract for prod_ingredient_dependency (PII columns excluded by the MDL projection)
select ingredient_id, ingredient_name, ingredient_category, products_using, pct_of_products, dependency_level, dependency_rank
from main_marts.prod_ingredient_dependency
