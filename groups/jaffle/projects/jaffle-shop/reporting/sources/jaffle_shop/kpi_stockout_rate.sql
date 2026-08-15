-- source extract for kpi_stockout_rate (PII columns excluded by the MDL projection)
select metric_month, location_id, stockout_products, total_products, stockout_rate_pct
from main_marts.kpi_stockout_rate
