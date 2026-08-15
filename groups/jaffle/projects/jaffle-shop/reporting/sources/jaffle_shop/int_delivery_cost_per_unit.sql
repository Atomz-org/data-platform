-- source extract for int_delivery_cost_per_unit (PII columns excluded by the MDL projection)
select shipment_id, cost_per_unit_delivered, transit_days, purchase_order_id, supplier_id, carrier, shipped_at, actual_arrival_at, units_delivered, po_total_cost
from main_marts.int_delivery_cost_per_unit
