-- source extract for rpt_ar_aging_summary (PII columns excluded by the MDL projection)
select aging_bucket, aging_bucket_sort, receivable_count, customer_count, total_outstanding, avg_outstanding, min_outstanding, max_outstanding, avg_days_past_due, grand_total_outstanding, pct_of_total
from main_marts.rpt_ar_aging_summary
