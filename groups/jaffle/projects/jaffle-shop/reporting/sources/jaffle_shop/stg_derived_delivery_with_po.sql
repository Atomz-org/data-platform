-- source extract for stg_derived_delivery_with_po (PII columns excluded by the MDL projection)
select shipment_id, purchase_order_id, supplier_id, po_ordered_at, po_total, shipped_at, actual_arrival_at, total_lead_time_days, shipment_status
from main_marts.stg_derived_delivery_with_po
