-- source extract for stg_derived_order_complete (PII columns excluded by the MDL projection)
select order_id, customer_id, customer_name, location_id, location_name, ordered_at, order_total, tax_paid, subtotal
from main_marts.stg_derived_order_complete
