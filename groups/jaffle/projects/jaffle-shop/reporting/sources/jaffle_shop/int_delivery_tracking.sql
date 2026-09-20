-- source extract for int_delivery_tracking (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    shipment_id,
    purchase_order_id,
    shipment_status,
    actual_transit_days,
    expected_transit_days,
    is_on_time
from main_marts.int_delivery_tracking
