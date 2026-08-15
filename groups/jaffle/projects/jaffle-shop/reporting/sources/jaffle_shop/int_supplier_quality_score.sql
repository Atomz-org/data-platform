-- source extract for int_supplier_quality_score (PII columns excluded by the MDL projection)
select supplier_id, total_quantity_received, total_quantity_rejected, defect_rate, quality_score, total_waste_quantity, total_waste_cost, total_receipts, rejected_receipts
from main_marts.int_supplier_quality_score
