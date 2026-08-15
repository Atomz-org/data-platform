-- source extract for kpi_overhead_ratio (PII columns excluded by the MDL projection)
select month_start, overhead_cost, monthly_revenue, overhead_ratio
from main_marts.kpi_overhead_ratio
