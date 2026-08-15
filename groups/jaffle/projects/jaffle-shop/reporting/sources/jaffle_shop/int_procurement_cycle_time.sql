-- source extract for int_procurement_cycle_time (PII columns excluded by the MDL projection)
select purchase_order_id, supplier_id, cycle_time_days, expected_cycle_time_days, cycle_time_variance_days, po_status, ordered_at, expected_delivery_at, first_received_at, last_received_at
from main_marts.int_procurement_cycle_time
