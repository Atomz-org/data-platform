-- source extract for fct_deliveries (PII columns excluded by the MDL projection)
select shipment_id, purchase_order_id, supplier_id, destination_id, destination_type, carrier, tracking_number, shipment_status, po_status, po_total_amount, destination_warehouse_name, destination_city, shipped_at, estimated_arrival_at, actual_arrival_at, actual_transit_days, expected_transit_days, is_on_time, is_delivered, is_delayed
from main_marts.fct_deliveries
