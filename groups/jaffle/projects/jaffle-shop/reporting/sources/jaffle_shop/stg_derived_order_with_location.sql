-- source extract for stg_derived_order_with_location (PII columns excluded by the MDL projection)
select order_id, customer_id, location_id, location_name, ordered_at, order_total, tax_paid, subtotal
from main_marts.stg_derived_order_with_location
