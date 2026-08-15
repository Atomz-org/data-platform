-- source extract for rpt_daily_revenue_kpis (PII columns excluded by the MDL projection)
select revenue_date, location_id, location_name, invoice_count, gross_revenue, tax_collected, total_revenue, avg_invoice_amount, transaction_count, completed_transaction_count, unique_orders_with_payments, revenue_per_order, transaction_success_rate
from main_marts.rpt_daily_revenue_kpis
