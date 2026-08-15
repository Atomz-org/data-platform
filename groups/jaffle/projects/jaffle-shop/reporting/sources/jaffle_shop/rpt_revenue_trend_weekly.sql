-- source extract for rpt_revenue_trend_weekly (PII columns excluded by the MDL projection)
select revenue_week, location_id, location_name, invoice_count, gross_revenue, tax_collected, total_revenue, avg_invoice_amount, active_days, prev_week_revenue, wow_growth_rate, rolling_4w_avg_revenue
from main_marts.rpt_revenue_trend_weekly
