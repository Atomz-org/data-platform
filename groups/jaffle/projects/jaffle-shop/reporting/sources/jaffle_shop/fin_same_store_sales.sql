-- source extract for fin_same_store_sales (PII columns excluded by the MDL projection)
select location_id, store_name, month_start, monthly_revenue, monthly_orders, revenue_same_month_last_year, orders_same_month_last_year, same_store_revenue_growth_pct, same_store_order_growth_pct
from main_marts.fin_same_store_sales
