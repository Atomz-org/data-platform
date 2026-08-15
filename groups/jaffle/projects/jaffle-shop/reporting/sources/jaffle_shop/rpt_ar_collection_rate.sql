-- source extract for rpt_ar_collection_rate (PII columns excluded by the MDL projection)
select report_month, receivables_created, total_amount_due, total_amount_collected, total_amount_outstanding, fully_collected_count, partially_collected_count, open_count, collection_rate, full_collection_rate, prev_month_collection_rate, rolling_3m_avg_collection_rate
from main_marts.rpt_ar_collection_rate
