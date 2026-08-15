-- source extract for rank_suppliers_by_lead_time (PII columns excluded by the MDL projection)
select supplier_id, avg_lead_time, min_lead_time, max_lead_time, delivery_count, lead_time_range, lead_time_rank, lead_time_quartile
from main_marts.rank_suppliers_by_lead_time
