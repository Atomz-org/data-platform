-- source extract for view_cfo_ar_summary (PII columns excluded by the MDL projection)
select aging_bucket, total_outstanding, receivable_count, customer_count, avg_outstanding, avg_days_past_due, pct_of_total, collection_priority
from main_marts.view_cfo_ar_summary
