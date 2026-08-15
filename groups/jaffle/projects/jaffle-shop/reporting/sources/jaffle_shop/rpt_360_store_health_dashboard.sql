-- source extract for rpt_360_store_health_dashboard (PII columns excluded by the MDL projection)
select location_id, health_score, health_tier, store_name, total_revenue, avg_operating_margin_pct, avg_labor_cost_pct, months_of_data, store_health_score, latest_monthly_revenue, latest_profit_margin, latest_labor_ratio
from main_marts.rpt_360_store_health_dashboard
