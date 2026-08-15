-- source extract for narrow_recent_orders (PII columns excluded by the MDL projection)
select order_id, customer_id, ordered_at
from main_marts.narrow_recent_orders
