-- source extract for rpt_store_performance_quadrant (PII columns excluded by the MDL projection)
select location_id, store_name, latest_revenue, revenue_growth_pct, net_profit_margin_pct, fleet_median_growth, fleet_median_margin, quadrant, strategic_recommendation
from main_marts.rpt_store_performance_quadrant
