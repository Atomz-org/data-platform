-- source extract for geo_customer_density_by_store (PII columns excluded by the MDL projection)
select location_id, store_name, order_month, unique_customers, prev_month_customers, mom_growth_pct, customer_trend
from main_marts.geo_customer_density_by_store
