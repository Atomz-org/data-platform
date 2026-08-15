-- source extract for sum_ytd_company_totals (PII columns excluded by the MDL projection)
select revenue_date, total_revenue, total_orders, ytd_revenue, ytd_orders, day_of_year
from main_marts.sum_ytd_company_totals
