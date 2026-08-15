-- source extract for narrow_top_10_stores (PII columns excluded by the MDL projection)
select location_id, location_name, total_revenue
from main_marts.narrow_top_10_stores
