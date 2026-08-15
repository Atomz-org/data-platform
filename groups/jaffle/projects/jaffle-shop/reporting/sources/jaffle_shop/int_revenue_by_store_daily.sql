-- source extract for int_revenue_by_store_daily (PII columns excluded by the MDL projection)
select revenue_date, location_id, location_name, store_opened_date, invoice_count, gross_revenue, total_revenue, rolling_7d_revenue, avg_7d_revenue, dod_growth_rate, tax_collected, avg_invoice_amount, prev_day_revenue
from main_marts.int_revenue_by_store_daily
