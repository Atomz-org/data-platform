-- source extract for geo_market_penetration (PII columns excluded by the MDL projection)
select location_id, store_name, months_of_data, total_revenue, avg_monthly_revenue, revenue_rank
from main_marts.geo_market_penetration
