-- source extract for sum_annual_company_summary (PII columns excluded by the MDL projection)
select fiscal_year, annual_revenue, annual_orders, annual_aov, avg_monthly_revenue, min_monthly_revenue, max_monthly_revenue
from main_marts.sum_annual_company_summary
