-- source extract for rpt_maintenance_cost_trend (PII columns excluded by the MDL projection)
select equipment_type, location_id, location_name, maintenance_month, event_count, total_cost, total_downtime_hours, emergency_events, warranty_covered_cost, out_of_pocket_cost, avg_cost_per_event, prev_month_cost, cost_change_pct, rolling_3mo_avg_cost
from main_marts.rpt_maintenance_cost_trend
