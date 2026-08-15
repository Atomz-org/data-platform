-- source extract for geo_regional_labor_cost (PII columns excluded by the MDL projection)
select location_id, store_name, month_start, monthly_labor_cost, monthly_labor_hours, cost_per_hour, fleet_avg_cost_per_hour, cost_per_hour_vs_fleet
from main_marts.geo_regional_labor_cost
