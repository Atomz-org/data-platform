-- source extract for view_coo_store_performance (PII columns excluded by the MDL projection)
select location_id, store_name, store_health_score, revenue_growth_score, profitability_score, labor_efficiency_score, performance_rank, performance_tier
from main_marts.view_coo_store_performance
