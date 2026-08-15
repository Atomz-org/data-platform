-- source extract for int_ar_balance_monthly (PII columns excluded by the MDL projection)
select month_start, open_receivables, total_outstanding, outstanding_current, outstanding_90_plus, total_amount_due, total_amount_paid, avg_outstanding_per_receivable, outstanding_1_30, outstanding_31_60, outstanding_61_90
from main_marts.int_ar_balance_monthly
