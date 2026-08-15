-- source extract for geo_store_maturity_curve (PII columns excluded by the MDL projection)
select months_since_opening, store_count, avg_revenue, min_revenue, max_revenue, median_revenue
from main_marts.geo_store_maturity_curve
