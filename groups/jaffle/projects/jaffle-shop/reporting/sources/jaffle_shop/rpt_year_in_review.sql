-- source extract for rpt_year_in_review (PII columns excluded by the MDL projection)
select fiscal_year, annual_revenue, revenue_yoy_growth_pct, annual_orders, avg_monthly_revenue, min_monthly_revenue, max_monthly_revenue, months_of_data, prev_year_revenue, prev_year_orders, avg_order_value
from main_marts.rpt_year_in_review
