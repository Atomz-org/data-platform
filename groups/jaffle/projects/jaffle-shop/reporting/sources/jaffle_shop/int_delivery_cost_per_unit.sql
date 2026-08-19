-- source extract for int_delivery_cost_per_unit (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    shipment_id,
    cost_per_unit_delivered,
    transit_days
from main_marts.int_delivery_cost_per_unit
