-- source extract for kpi_labor_cost_ratio (PII columns excluded by the MDL projection)
select month_start, location_id, monthly_labor_cost, monthly_revenue, labor_cost_ratio
from main_marts.kpi_labor_cost_ratio
