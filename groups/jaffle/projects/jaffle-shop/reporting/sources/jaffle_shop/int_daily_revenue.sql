-- source extract for int_daily_revenue (PII columns excluded by the MDL projection)
select revenue_date, location_id, location_name, invoice_count, gross_revenue, tax_collected, total_revenue, avg_invoice_amount
from main_marts.int_daily_revenue
