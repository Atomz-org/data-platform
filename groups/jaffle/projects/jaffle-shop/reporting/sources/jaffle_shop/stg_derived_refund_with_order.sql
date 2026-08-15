-- source extract for stg_derived_refund_with_order (PII columns excluded by the MDL projection)
select refund_id, order_id, customer_id, location_id, order_total, requested_date, refund_amount, refund_reason, refund_pct_of_order
from main_marts.stg_derived_refund_with_order
