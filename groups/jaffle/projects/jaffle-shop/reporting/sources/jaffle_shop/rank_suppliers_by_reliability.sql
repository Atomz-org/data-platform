-- source extract for rank_suppliers_by_reliability (PII columns excluded by the MDL projection)
select supplier_id, total_deliveries, on_time_pct, avg_lead_time, reliability_rank, reliability_quartile
from main_marts.rank_suppliers_by_reliability
