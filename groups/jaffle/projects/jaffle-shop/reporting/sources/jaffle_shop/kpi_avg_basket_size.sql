-- source extract for kpi_avg_basket_size (PII columns excluded by the MDL projection)
select order_month, total_orders, total_items, avg_basket_size, prior_month_basket
from main_marts.kpi_avg_basket_size
