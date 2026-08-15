-- source extract for coh_product_adoption_curve (PII columns excluded by the MDL projection)
select product_id, product_name, first_sale_date, units_first_30d, units_first_90d, revenue_first_180d, units_first_60d, units_first_180d, orders_first_30d, orders_first_60d, orders_first_90d, orders_first_180d, revenue_first_30d, revenue_first_90d, total_units_all_time, days_on_market
from main_marts.coh_product_adoption_curve
