-- source extract for kpi_supplier_on_time_delivery (PII columns excluded by the MDL projection)
select delivery_month, supplier_id, total_deliveries, on_time_count, on_time_pct
from main_marts.kpi_supplier_on_time_delivery
