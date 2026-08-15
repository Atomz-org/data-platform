-- source extract for rank_suppliers_by_cost (PII columns excluded by the MDL projection)
select supplier_id, total_spend, po_count, avg_po_value, spend_rank, spend_share_pct
from main_marts.rank_suppliers_by_cost
