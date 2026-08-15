-- source extract for int_refund_rate_by_store (PII columns excluded by the MDL projection)
select location_id, report_month, invoice_count, total_invoice_amount, refund_count, total_refund_amount, refund_rate, refund_amount_rate, avg_days_to_resolution, avg_refund_amount, approved_refund_count
from main_marts.int_refund_rate_by_store
