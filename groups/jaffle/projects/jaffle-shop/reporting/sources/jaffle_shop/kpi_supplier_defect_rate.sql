-- source extract for kpi_supplier_defect_rate (PII columns excluded by the MDL projection)
select receipt_month, supplier_id, total_receipts, defects, defect_rate_pct
from main_marts.kpi_supplier_defect_rate
