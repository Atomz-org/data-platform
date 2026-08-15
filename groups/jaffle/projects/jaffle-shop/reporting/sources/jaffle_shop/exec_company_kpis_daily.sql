-- source extract for exec_company_kpis_daily (PII columns excluded by the MDL projection)
select kpi_date, total_revenue, total_orders, active_customers, avg_ticket_size, total_gross_revenue, total_tax_collected, new_customers, returning_customers, total_waste_cost, total_waste_events, net_revenue_after_waste, revenue_7d_avg, orders_7d_avg
from main_marts.exec_company_kpis_daily
