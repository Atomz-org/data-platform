-- source extract for int_refunds_enriched (PII columns excluded by the MDL projection)
select refund_id, refund_amount, refund_pct_of_invoice, days_to_resolution, order_id, invoice_id, refund_reason, refund_status, requested_date, resolved_date, invoice_total, invoice_status, order_total, location_id, order_date
from main_marts.int_refunds_enriched
