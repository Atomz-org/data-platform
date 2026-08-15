-- source extract for rpt_seasonal_revenue_pattern (PII columns excluded by the MDL projection)
select revenue_month, revenue_year, month_of_year, location_id, location_name, gross_revenue, total_revenue, invoice_count, avg_invoice_amount, avg_revenue_for_month, seasonal_index, overall_avg_monthly_revenue, month_vs_overall_ratio, same_month_prev_year_revenue, yoy_growth_rate
from main_marts.rpt_seasonal_revenue_pattern
