-- source extract for fct_refunds (PII columns excluded by the MDL projection)
select refund_id, order_id, invoice_id, location_id, refund_reason, refund_status, refund_amount, invoice_total, order_total, refund_pct_of_invoice, requested_date, resolved_date, order_date, days_to_resolution, is_approved, is_full_refund
from main_marts.fct_refunds
