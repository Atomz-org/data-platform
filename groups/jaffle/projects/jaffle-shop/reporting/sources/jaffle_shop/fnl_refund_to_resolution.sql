-- source extract for fnl_refund_to_resolution (PII columns excluded by the MDL projection)
select refund_month, total_refund_requests, approved, denied, approval_rate_pct, avg_days_to_resolution, reviewed, processed, total_approved_amount, full_refund_pct
from main_marts.fnl_refund_to_resolution
