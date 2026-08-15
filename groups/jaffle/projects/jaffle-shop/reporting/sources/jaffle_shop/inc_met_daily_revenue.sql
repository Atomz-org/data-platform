-- source extract for inc_met_daily_revenue (PII columns excluded by the MDL projection)
select revenue_key, customer_id, revenue_date, daily_revenue, daily_tax, invoice_count
from main_marts.inc_met_daily_revenue
