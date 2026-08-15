-- source extract for geo_store_risk_assessment (PII columns excluded by the MDL projection)
select location_id, store_health_score, avg_margin_pct, avg_labor_ratio_pct, declining_revenue_flag, high_labor_cost_flag, low_health_score_flag, low_margin_flag, total_risk_flags, risk_level
from main_marts.geo_store_risk_assessment
