-- source extract for fin_refund_turnaround (PII columns excluded by the MDL projection)
select refund_month, refund_reason, total_refunds, completed_refunds, avg_turnaround_days, min_turnaround_days, max_turnaround_days, pct_within_1_day, pct_within_3_days, pct_within_7_days, total_refund_amount
from main_marts.fin_refund_turnaround
