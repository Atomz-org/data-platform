-- source extract for int_accounts_receivable_aging (PII columns excluded by the MDL projection)
select receivable_id, customer_id, amount_outstanding, days_past_due, aging_bucket, aging_bucket_sort, invoice_id, receivable_status, amount_due, amount_paid, due_date, created_date
from main_marts.int_accounts_receivable_aging
