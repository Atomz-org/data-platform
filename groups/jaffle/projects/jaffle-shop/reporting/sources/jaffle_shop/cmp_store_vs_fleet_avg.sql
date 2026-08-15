-- source extract for cmp_store_vs_fleet_avg (PII columns excluded by the MDL projection)
select location_id, store_name, store_revenue, fleet_avg_revenue, revenue_vs_fleet_pct, margin_vs_fleet_pp, revenue_rank, revenue_vs_fleet, store_margin_pct, fleet_avg_margin_pct, store_labor_pct, fleet_avg_labor_pct, labor_vs_fleet_pp, store_employees, fleet_avg_employee_count, margin_rank
from main_marts.cmp_store_vs_fleet_avg
