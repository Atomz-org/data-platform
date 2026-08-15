-- source extract for rpt_food_cost_variance_alert (PII columns excluded by the MDL projection)
select location_id, store_name, report_month, monthly_revenue, monthly_cogs, food_cost_pct, fleet_avg_food_cost_pct, variance_from_fleet, alert_level
from main_marts.rpt_food_cost_variance_alert
