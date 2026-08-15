-- source extract for rpt_refund_reason_breakdown (PII columns excluded by the MDL projection)
select refund_reason, location_id, report_month, refund_count, total_refund_amount, avg_refund_amount, approved_count, full_refund_count, avg_days_to_resolution, location_month_refund_count, reason_share_pct, reason_amount_share_pct
from main_marts.rpt_refund_reason_breakdown
