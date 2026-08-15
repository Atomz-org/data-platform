-- source extract for kpi_revenue_per_store (PII columns excluded by the MDL projection)
select month_start, store_count, monthly_revenue, revenue_per_store, prior_month_rps
from main_marts.kpi_revenue_per_store
