-- source extract for kpi_maintenance_cost_ratio (PII columns excluded by the MDL projection)
select maint_month, location_id, total_maintenance_cost, monthly_revenue, maintenance_cost_ratio
from main_marts.kpi_maintenance_cost_ratio
