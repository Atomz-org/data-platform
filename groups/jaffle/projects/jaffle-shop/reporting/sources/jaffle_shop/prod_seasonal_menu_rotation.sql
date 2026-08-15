-- source extract for prod_seasonal_menu_rotation (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, season_type, seasonality_index, monthly_quantity, rotation_recommendation, season_rank
from main_marts.prod_seasonal_menu_rotation
