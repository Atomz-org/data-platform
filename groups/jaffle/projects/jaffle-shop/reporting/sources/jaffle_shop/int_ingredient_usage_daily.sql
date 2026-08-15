-- source extract for int_ingredient_usage_daily (PII columns excluded by the MDL projection)
select order_date, ingredient_id, quantity_unit, total_quantity_used, order_item_count
from main_marts.int_ingredient_usage_daily
