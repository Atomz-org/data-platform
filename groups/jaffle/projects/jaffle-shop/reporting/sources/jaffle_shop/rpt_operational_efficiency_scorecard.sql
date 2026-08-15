-- source extract for rpt_operational_efficiency_scorecard (PII columns excluded by the MDL projection)
select store_name, store_id, total_orders, avg_orders_per_hour, max_orders_in_hour, store_total_peak_hours, store_peak_hours_share_pct, busiest_hour, avg_revenue_per_labor_hour, avg_revenue_per_employee, total_labor_hours, avg_staffing_ratio, rev_per_hour_vs_fleet, orders_per_hour_vs_fleet, efficiency_score, efficiency_rank
from main_marts.rpt_operational_efficiency_scorecard
