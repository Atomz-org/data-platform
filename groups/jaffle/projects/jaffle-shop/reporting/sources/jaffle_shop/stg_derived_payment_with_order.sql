-- source extract for stg_derived_payment_with_order (PII columns excluded by the MDL projection)
select payment_transaction_id, order_id, customer_id, location_id, ordered_at, payment_method, payment_amount, processed_date, payment_status
from main_marts.stg_derived_payment_with_order
