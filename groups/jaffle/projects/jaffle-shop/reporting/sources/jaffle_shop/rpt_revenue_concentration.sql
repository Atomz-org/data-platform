-- source extract for rpt_revenue_concentration (PII columns excluded by the MDL projection)
select customer_id, customer_name, invoice_count, total_revenue, avg_invoice_amount, first_invoice_date, last_invoice_date, grand_total_revenue, total_customer_count, revenue_share_pct, revenue_rank, revenue_decile, cumulative_revenue, cumulative_revenue_pct, concentration_tier
from main_marts.rpt_revenue_concentration
