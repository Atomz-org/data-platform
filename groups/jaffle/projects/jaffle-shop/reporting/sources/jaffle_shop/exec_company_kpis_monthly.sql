-- source extract for exec_company_kpis_monthly (PII columns excluded by the MDL projection)
select month_start, monthly_revenue, mom_revenue_growth, yoy_revenue_growth, monthly_orders, monthly_gross_revenue, monthly_tax, avg_ticket_size, monthly_new_customers, avg_daily_active_customers, monthly_waste_cost, active_days, prev_month_revenue, mom_orders_growth, same_month_last_year_revenue
from main_marts.exec_company_kpis_monthly
