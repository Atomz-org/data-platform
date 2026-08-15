-- source extract for kpi_procurement_cycle_time (PII columns excluded by the MDL projection)
select order_month, supplier_id, avg_cycle_time, min_cycle_time, max_cycle_time, po_count
from main_marts.kpi_procurement_cycle_time
