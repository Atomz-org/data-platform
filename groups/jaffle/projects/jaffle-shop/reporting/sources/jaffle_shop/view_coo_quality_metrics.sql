-- source extract for view_coo_quality_metrics (PII columns excluded by the MDL projection)
select total_waste_events, total_waste_cost, avg_waste_cost_per_product, products_with_waste, total_suppliers, avg_supplier_quality, low_quality_suppliers, waste_severity
from main_marts.view_coo_quality_metrics
