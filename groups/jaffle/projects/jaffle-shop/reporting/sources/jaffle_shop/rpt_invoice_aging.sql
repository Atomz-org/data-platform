-- source extract for rpt_invoice_aging (PII columns excluded by the MDL projection)
select invoice_id, order_id, customer_id, customer_name, location_id, invoice_status, subtotal, tax_amount, total_amount, amount_paid, amount_due, issued_date, due_date, days_overdue, aging_bucket, aging_bucket_sort, bucket_total_due, grand_total_due, pct_of_total_due, customer_unpaid_invoice_count
from main_marts.rpt_invoice_aging
