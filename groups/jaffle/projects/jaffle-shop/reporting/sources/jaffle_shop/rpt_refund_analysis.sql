-- source extract for rpt_refund_analysis (PII columns excluded by the MDL projection)
select report_month, location_id, refund_reason, refund_count, approved_refund_count, total_refund_amount, approved_refund_amount, avg_refund_amount, avg_days_to_resolution, full_refund_count, total_invoice_count, total_invoice_amount, refund_rate, refund_amount_rate
from main_marts.rpt_refund_analysis
