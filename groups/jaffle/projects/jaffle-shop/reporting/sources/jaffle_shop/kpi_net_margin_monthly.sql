-- source extract for kpi_net_margin_monthly (PII columns excluded by the MDL projection)
select month_start, monthly_revenue, total_expenses, net_income, net_margin_pct
from main_marts.kpi_net_margin_monthly
