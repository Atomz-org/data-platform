-- source extract for dq_orphan_orders (PII columns excluded by the MDL projection)
select order_id, customer_id, order_total, location_id, ordered_at, subtotal
from main_marts.dq_orphan_orders
