-- source extract for fin_revenue_per_sqft_proxy (PII columns excluded by the MDL projection)
select location_id, store_name, month_start, monthly_revenue, opened_date, months_open, size_proxy_factor, normalized_revenue
from main_marts.fin_revenue_per_sqft_proxy
