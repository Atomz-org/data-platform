-- source extract for rpt_monthly_pnl_by_store (PII columns excluded by the MDL projection)
select location_id, location_name, report_month, gross_revenue, tax_collected, total_revenue, cost_of_goods_sold, gross_profit, operating_expenses, operating_income, total_expenses, net_income, gross_margin_pct, net_margin_pct
from main_marts.rpt_monthly_pnl_by_store
