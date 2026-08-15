-- source extract for kpi_revenue_per_customer (PII columns excluded by the MDL projection)
select month_start, monthly_revenue, tracked_active_customers, revenue_per_customer
from main_marts.kpi_revenue_per_customer
