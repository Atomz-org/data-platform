-- source extract for adv_cumulative_with_reset (PII columns excluded by the MDL projection)
select revenue_date, location_id, location_name, fiscal_year, fiscal_quarter, fiscal_quarter_label, daily_revenue, invoice_count, day_of_quarter, qtd_cumulative_revenue, qtd_cumulative_invoices, qtd_avg_daily_revenue, all_time_cumulative_revenue
from main_marts.adv_cumulative_with_reset
