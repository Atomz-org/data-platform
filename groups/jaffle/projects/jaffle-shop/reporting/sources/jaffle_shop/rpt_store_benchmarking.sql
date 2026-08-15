-- source extract for rpt_store_benchmarking (PII columns excluded by the MDL projection)
select store_id, store_name, total_revenue, fleet_avg_revenue, revenue_vs_fleet, avg_operating_margin_pct, fleet_avg_margin, margin_vs_fleet, avg_labor_cost_pct, fleet_avg_labor_pct, labor_pct_vs_fleet, revenue_per_employee, fleet_avg_revenue_per_employee, margin_performance, labor_cost_flag, revenue_rank, margin_rank
from main_marts.rpt_store_benchmarking
