-- source extract for int_store_labor_pct (PII columns excluded by the MDL projection)
select store_id, report_month, labor_cost_pct, fleet_avg_labor_pct, location_id, month_start, monthly_revenue, monthly_labor_cost, labor_pct_vs_fleet
from main_marts.int_store_labor_pct
