-- source extract for int_seasonal_product_index (PII columns excluded by the MDL projection)
select product_id, sales_month, seasonality_index, season_type, month_number, monthly_quantity, monthly_revenue, avg_monthly_quantity
from main_marts.int_seasonal_product_index
