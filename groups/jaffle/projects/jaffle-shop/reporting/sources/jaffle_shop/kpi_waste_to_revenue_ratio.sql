-- source extract for kpi_waste_to_revenue_ratio (PII columns excluded by the MDL projection)
select month_start, location_id, monthly_waste_cost, monthly_revenue, waste_to_revenue_pct
from main_marts.kpi_waste_to_revenue_ratio
