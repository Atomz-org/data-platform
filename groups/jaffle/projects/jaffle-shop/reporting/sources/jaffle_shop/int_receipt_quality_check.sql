-- source extract for int_receipt_quality_check (PII columns excluded by the MDL projection)
select purchase_order_id, quality_pass_rate_pct, total_receipts, total_quantity_received, passed_count, failed_count, partial_count, first_receipt_date, last_receipt_date
from main_marts.int_receipt_quality_check
