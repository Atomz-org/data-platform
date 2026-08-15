-- source extract for int_revenue_concentration_index (PII columns excluded by the MDL projection)
select location_id, herfindahl_index, concentration_level, customer_count, store_total_revenue
from main_marts.int_revenue_concentration_index
