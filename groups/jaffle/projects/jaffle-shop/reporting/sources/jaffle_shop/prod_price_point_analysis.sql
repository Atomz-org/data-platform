-- source extract for prod_price_point_analysis (PII columns excluded by the MDL projection)
select product_id, price_changed_date, old_price, new_price, price_change, price_change_pct, pre_change_qty, post_change_qty, quantity_change, quantity_change_pct, price_elasticity_estimate
from main_marts.prod_price_point_analysis
