-- source extract for int_refund_processing_time (PII columns excluded by the MDL projection)
select refund_id, processing_days, processing_speed_tier, order_id, invoice_id, refund_reason, refund_status, refund_amount, requested_date, resolved_date
from main_marts.int_refund_processing_time
