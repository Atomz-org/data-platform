-- source extract for sum_quarterly_supplier_totals (PII columns excluded by the MDL projection)
select order_quarter, supplier_id, quarterly_spend, quarterly_pos, avg_po_value
from main_marts.sum_quarterly_supplier_totals
