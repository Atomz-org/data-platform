-- source extract for rpt_supplier_quality_ranking (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, is_active, total_quantity_received, total_quantity_rejected, defect_rate, quality_score, total_waste_quantity, total_waste_cost, total_receipts, rejected_receipts, quality_rank, quality_tier
from main_marts.rpt_supplier_quality_ranking
