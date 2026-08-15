-- source extract for scr_store_health (PII columns excluded by the MDL projection)
select location_id, store_health_score, health_tier, store_name, total_revenue, avg_operating_margin_pct, avg_labor_cost_pct, revenue_growth_score, profitability_score, labor_efficiency_score, inventory_health_score
from main_marts.scr_store_health
