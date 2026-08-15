-- source extract for kpi_revenue_per_order (PII columns excluded by the MDL projection)
select month_start, monthly_revenue, total_orders, revenue_per_order, prior_month_rpo
from main_marts.kpi_revenue_per_order
