-- source extract for rpt_store_profitability (PII columns excluded by the MDL projection)
select location_id, location_name, report_month, gross_revenue, total_revenue, invoice_count, total_expenses, cogs, operating_expenses, gross_profit, net_income, gross_margin_pct, net_margin_pct, revenue_per_invoice, prev_month_net_income
from main_marts.rpt_store_profitability
