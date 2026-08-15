-- source extract for int_delivery_on_time_rate (PII columns excluded by the MDL projection)
select supplier_id, total_deliveries, on_time_deliveries, late_deliveries, on_time_rate, avg_transit_days, pending_deliveries, avg_expected_transit_days
from main_marts.int_delivery_on_time_rate
