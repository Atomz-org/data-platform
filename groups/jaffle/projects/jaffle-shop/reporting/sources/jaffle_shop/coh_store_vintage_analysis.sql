-- source extract for coh_store_vintage_analysis (PII columns excluded by the MDL projection)
select opening_year, months_since_opening, stores_in_vintage, avg_revenue_per_store, total_orders, total_revenue, avg_orders_per_store, avg_customers_per_store
from main_marts.coh_store_vintage_analysis
