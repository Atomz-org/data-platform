-- source extract for int_delivery_tracking (PII columns excluded by the MDL projection)
select shipment_id, purchase_order_id, shipment_status, actual_transit_days, expected_transit_days, is_on_time, supplier_id, destination_id, destination_type, carrier, tracking_number, shipped_at, estimated_arrival_at, actual_arrival_at, po_status, po_total_amount, destination_warehouse_name, destination_city
from main_marts.int_delivery_tracking
