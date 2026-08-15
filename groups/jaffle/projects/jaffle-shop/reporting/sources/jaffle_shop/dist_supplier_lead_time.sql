-- source extract for dist_supplier_lead_time (PII columns excluded by the MDL projection)
select supplier_id, delivery_count, mean_lead_time, median_lead_time, p90_lead_time, min_lead_time, max_lead_time, lead_time_range
from main_marts.dist_supplier_lead_time
