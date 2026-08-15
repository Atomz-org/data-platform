-- source extract for rpt_delivery_performance_monthly (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, delivery_month, total_shipments, on_time_shipments, late_shipments, pending_shipments, avg_transit_days, avg_expected_transit_days, monthly_on_time_rate
from main_marts.rpt_delivery_performance_monthly
